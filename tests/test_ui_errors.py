import unittest

from aniflow.database.errors import (
    DatabaseCorruptError,
    DatabaseRestoreError,
    DatabaseTooNewError,
    MigrationError,
    SettingsError,
)
from aniflow.net.local_only import NotLocalError
from aniflow.services.ai.errors import (
    AICapabilityError,
    AIModelMissingError,
    AINotLocalError,
    AIResponseError,
    AIUnavailableError,
)
from aniflow.services.anilist.errors import (
    AniListGraphQLError,
    AniListHttpError,
    AniListNetworkError,
    AniListNotFoundError,
    AniListRateLimitError,
    AniListResponseError,
    AniListTimeoutError,
)
from aniflow.ui.errors import GENERIC_MESSAGE, GENERIC_TITLE, MAX_DETAILS, describe_exception
from aniflow.ui.navigation import UnknownSectionError

# (exception, titre attendu, « Réessayer » pertinent)
SERVICE_ERRORS = [
    (AniListNetworkError(), "Connexion impossible", True),
    (AniListTimeoutError(), "Délai dépassé", True),
    (AniListRateLimitError(12), "Trop de requêtes", True),
    (AniListNotFoundError(), "Introuvable", False),
    (AniListHttpError(503), "Erreur AniList", True),
    (AniListHttpError(403), "Erreur AniList", False),
    (AniListGraphQLError(["champ inconnu"]), "Erreur AniList", False),
    (AniListResponseError(), "Réponse illisible", True),
    (AIUnavailableError(url="http://127.0.0.1:11434"), "IA locale indisponible", True),
    (AIModelMissingError("gemma4:e2b"), "IA locale", False),
    (AINotLocalError("x", user_message="Adresse non locale."), "IA locale", False),
    (AICapabilityError("x", user_message="Modalité absente."), "IA locale", False),
    (AIResponseError("x", detail="mémoire insuffisante"), "IA locale", True),
    (NotLocalError("x", "Adresse non locale."), "IA locale", False),
    (DatabaseTooNewError(5, 3), "Base de données", False),
    (DatabaseCorruptError(), "Base de données", False),
    (DatabaseRestoreError(), "Base de données", False),
    (MigrationError(2, "boom"), "Base de données", False),
    (SettingsError("x", user_message="Valeur invalide."), "Réglage invalide", False),
    (UnknownSectionError("zzz"), "Section inconnue", False),
]


class ServiceErrorTests(unittest.TestCase):
    def test_message_of_every_service_error_is_kept_exactly(self):
        for exc, title, retryable in SERVICE_ERRORS:
            with self.subTest(type(exc).__name__, status=getattr(exc, "status", None)):
                described = describe_exception(exc)
                self.assertEqual(described.message, exc.user_message)
                self.assertEqual((described.title, described.retryable, described.known), (title, retryable, True))
                self.assertTrue(described.details.startswith(type(exc).__name__ + ":"))


class UnknownErrorTests(unittest.TestCase):
    def test_technical_text_never_reaches_the_message(self):
        described = describe_exception(ValueError("jeton-secret-123 introuvable"))
        self.assertEqual((described.title, described.message), (GENERIC_TITLE, GENERIC_MESSAGE))
        self.assertNotIn("jeton-secret-123", described.message)
        self.assertIn("jeton-secret-123", described.details)
        self.assertEqual((described.known, described.retryable), (False, False))

    def test_builtin_exceptions_are_generic(self):
        for exc in (KeyError("clé"), OSError(13, "Accès refusé"), RuntimeError(), ZeroDivisionError("x")):
            with self.subTest(type(exc).__name__):
                self.assertEqual(describe_exception(exc).message, GENERIC_MESSAGE)

    def test_details_are_truncated(self):
        described = describe_exception(RuntimeError("x" * 5000))
        self.assertLessEqual(len(described.details), MAX_DETAILS)
        self.assertTrue(described.details.endswith("…"))

    def test_describing_a_broken_exception_never_raises(self):
        class BrokenStr(Exception):
            def __str__(self):
                raise RuntimeError("str défaillant")

        class BrokenProperty(Exception):
            @property
            def user_message(self):
                raise RuntimeError("propriété défaillante")

        self.assertIn("(message illisible)", describe_exception(BrokenStr()).details)
        self.assertEqual(describe_exception(BrokenProperty("x")).message, GENERIC_MESSAGE)

    def test_blank_or_non_text_user_message_is_ignored(self):
        for value in ("", "   ", None, 3, ["x"]):
            with self.subTest(value=value):
                exc = RuntimeError("x")
                exc.user_message = value
                self.assertEqual(describe_exception(exc).message, GENERIC_MESSAGE)

    def test_any_exception_carrying_a_user_message_is_known(self):
        class Future(Exception):
            user_message = "Message d'un futur service."

        described = describe_exception(Future("technique"))
        self.assertEqual((described.message, described.title, described.known), ("Message d'un futur service.", "Erreur", True))


if __name__ == "__main__":
    unittest.main()
