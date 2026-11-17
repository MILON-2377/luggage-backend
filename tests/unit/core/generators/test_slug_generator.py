import pytest

from app.core.generators.slug_generator import SlugGenerator


@pytest.fixture
def generator() -> SlugGenerator:
    return SlugGenerator()


class TestBasicSlugging:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Industrial Valve", "industrial-valve"),
            ("  Industrial Valve  ", "industrial-valve"),
            ("INDUSTRIAL VALVE", "industrial-valve"),
            ("industrial-valve", "industrial-valve"),
            ("industrial_valve", "industrial-valve"),
            ("Valve   DN50", "valve-dn50"),
            ("Valve --- DN50", "valve-dn50"),
            ("--Valve--", "valve"),
            ("Valve / Pump & Fitting", "valve-pump-fitting"),
            ("Model #2040 (SS316)", "model-2040-ss316"),
            ("2040", "2040"),
        ],
    )
    def test_generates_expected_slug(
        self, generator: SlugGenerator, value: str, expected: str
    ) -> None:
        assert generator.generate(value) == expected

    def test_is_deterministic(self, generator: SlugGenerator) -> None:
        assert generator.generate("Industrial Valve") == generator.generate(
            "Industrial Valve"
        )

    def test_is_idempotent(self, generator: SlugGenerator) -> None:
        once = generator.generate("Valve / Pump & Fitting")
        assert generator.generate(once) == once


class TestUnicodeHandling:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Café Crème", "cafe-creme"),
            ("Über Größe", "uber-groe"),
            ("Señor Niño", "senor-nino"),
            ("Ångström", "angstrom"),
            ("ＡＢＣ　１２３", "abc-123"),
        ],
    )
    def test_strips_accents_and_normalizes_width(
        self, generator: SlugGenerator, value: str, expected: str
    ) -> None:
        assert generator.generate(value) == expected

    @pytest.mark.parametrize("value", ["不锈钢阀门", "🔥🔥🔥", "!!!", "   ", ""])
    def test_returns_fallback_when_nothing_ascii_remains(
        self, generator: SlugGenerator, value: str
    ) -> None:
        assert generator.generate(value) == "item"

    def test_keeps_ascii_part_of_mixed_text(self, generator: SlugGenerator) -> None:
        assert generator.generate("不锈钢 Valve 阀门") == "valve"


class TestFallback:
    def test_custom_fallback(self) -> None:
        generator = SlugGenerator(fallback="category")
        assert generator.generate("不锈钢") == "category"

    def test_fallback_not_used_when_slug_exists(self) -> None:
        generator = SlugGenerator(fallback="category")
        assert generator.generate("Valves") == "valves"


class TestMaxLength:
    def test_truncates_to_max_length(self) -> None:
        generator = SlugGenerator(max_length=10)
        slug = generator.generate("abcdefghijklmnopqrstuvwxyz")
        assert slug == "abcdefghij"
        assert len(slug) == 10

    def test_does_not_end_with_hyphen_after_truncation(self) -> None:
        generator = SlugGenerator(max_length=6)
        slug = generator.generate("abcde fghij")
        assert slug == "abcde"
        assert not slug.endswith("-")

    def test_default_max_length_is_150(self, generator: SlugGenerator) -> None:
        assert len(generator.generate("a" * 500)) == 150

    def test_short_value_is_untouched(self) -> None:
        generator = SlugGenerator(max_length=50)
        assert generator.generate("valve") == "valve"


class TestRandomSuffix:
    def test_appends_suffix_of_requested_length(
        self, generator: SlugGenerator
    ) -> None:
        slug = generator.generate("Industrial Valve", random_suffix_length=6)
        base, _, suffix = slug.rpartition("-")
        assert base == "industrial-valve"
        assert len(suffix) == 6

    def test_suffix_uses_only_lowercase_alphanumerics(
        self, generator: SlugGenerator
    ) -> None:
        for _ in range(50):
            suffix = generator.generate("x", random_suffix_length=8).rpartition("-")[2]
            assert suffix.isalnum()
            assert suffix == suffix.lower()

    def test_suffixes_differ_between_calls(self, generator: SlugGenerator) -> None:
        slugs = {
            generator.generate("Industrial Valve", random_suffix_length=8)
            for _ in range(100)
        }
        assert len(slugs) == 100

    def test_zero_length_adds_no_suffix(self, generator: SlugGenerator) -> None:
        assert generator.generate("Valve", random_suffix_length=0) == "valve"

    def test_fallback_gets_suffix_for_non_latin_input(
        self, generator: SlugGenerator
    ) -> None:
        slug = generator.generate("不锈钢阀门", random_suffix_length=6)
        assert slug.startswith("item-")
        assert len(slug) == len("item-") + 6

    def test_total_length_never_exceeds_max_length(self) -> None:
        generator = SlugGenerator(max_length=20)
        slug = generator.generate("a" * 100, random_suffix_length=6)
        assert len(slug) <= 20
        assert slug.startswith("a" * 13)

    def test_base_truncation_does_not_leave_double_hyphen(self) -> None:
        generator = SlugGenerator(max_length=12)
        slug = generator.generate("abcde fghij klmno", random_suffix_length=6)
        assert "--" not in slug
        assert len(slug) <= 12


class TestOutputFormat:
    @pytest.mark.parametrize(
        "value",
        [
            "Industrial Valve",
            "Café Crème",
            "Valve / Pump & Fitting",
            "不锈钢阀门",
            "  --weird__input!!  ",
        ],
    )
    def test_matches_database_slug_check_constraint(
        self, generator: SlugGenerator, value: str
    ) -> None:
        import re

        for suffix_length in (0, 6):
            slug = generator.generate(value, random_suffix_length=suffix_length)
            assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug)