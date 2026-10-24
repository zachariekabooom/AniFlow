import unittest

from aniflow.services.anilist.errors import AniListResponseError
from aniflow.services.anilist.models import (
    UNKNOWN_TITLE,
    FuzzyDate,
    MediaTitle,
    parse_media_details,
    parse_media_summary,
    parse_search_page,
)
from tests.support import fixtures


class FuzzyDateTests(unittest.TestCase):
    def test_iso_precision_levels(self):
        self.assertEqual(FuzzyDate(2023, 9, 29).iso(), "2023-09-29")
        self.assertEqual(FuzzyDate(2024, 3, None).iso(), "2024-03")
        self.assertEqual(FuzzyDate(2024, None, None).iso(), "2024")
        self.assertIsNone(FuzzyDate().iso())

    def test_parse_tolerates_garbage(self):
        self.assertEqual(FuzzyDate.parse(None), FuzzyDate())
        self.assertEqual(FuzzyDate.parse({"year": "2020", "month": True, "day": 5}), FuzzyDate(None, None, 5))


class MediaTitleTests(unittest.TestCase):
    def test_display_fallback_chain(self):
        title = MediaTitle(romaji=None, english="English", native="日本語")
        self.assertEqual(title.display("romaji"), "English")
        self.assertEqual(title.display("native"), "日本語")
        self.assertEqual(title.display("english"), "English")

    def test_unknown_title_is_explicit(self):
        self.assertEqual(MediaTitle().display(), UNKNOWN_TITLE)


class ParsingTests(unittest.TestCase):
    def test_summary_known_fields(self):
        s = parse_media_summary(fixtures.media_node(1001, title="Alpha"))
        self.assertEqual((s.id, s.id_mal, s.format, s.episodes, s.duration_min), (1001, 11001, "TV", 12, 24))
        self.assertEqual(s.title.display(), "Alpha")
        self.assertEqual(s.synonyms, ("Alias A", "Alias B"))  # entrée vide supprimée
        self.assertEqual(s.start_date.iso(), "2023-09-29")
        self.assertEqual(s.end_date.iso(), "2024-03")
        self.assertEqual(s.cover_url, "https://img.example/1001-xl.jpg")
        self.assertIs(s.is_adult, False)

    def test_missing_data_stays_unknown_never_invented(self):
        s = parse_media_summary({"id": 7})
        self.assertIsNone(s.episodes)
        self.assertIsNone(s.format)
        self.assertIsNone(s.is_adult)
        self.assertIsNone(s.cover_url)
        self.assertEqual(s.genres, ())
        self.assertEqual(s.title.display(), UNKNOWN_TITLE)

    def test_invalid_id_raises(self):
        for bad in (None, {}, {"id": "3"}, {"id": 0}, {"id": True}, {"id": -2}, []):
            with self.subTest(bad=bad), self.assertRaises(AniListResponseError):
                parse_media_summary(bad)

    def test_details_relations_and_skipped_edges_are_counted(self):
        d = parse_media_details(fixtures.details_node(1001))
        self.assertEqual([r.relation_type for r in d.relations], ["SEQUEL", "SOURCE", "SUMMARY"])
        self.assertEqual(d.skipped_relations, 1)  # l'arête sans nœud est signalée, pas ignorée en silence
        manga = d.relations[1].node
        self.assertEqual((manga.media_type, manga.format), ("MANGA", "MANGA"))
        self.assertEqual(d.average_score, 84)
        self.assertEqual([t.name for t in d.tags], ["Elf"])
        self.assertIn("Seconde ligne", d.description)

    def test_search_page(self):
        page = parse_search_page(fixtures.search_response([1, 2], has_next=True, total=57)["data"])
        self.assertEqual([i.id for i in page.items], [1, 2])
        self.assertEqual((page.total, page.has_next_page, page.current_page), (57, True, 1))

    def test_search_page_without_page_raises(self):
        with self.assertRaises(AniListResponseError):
            parse_search_page({"Media": {}})


if __name__ == "__main__":
    unittest.main()
