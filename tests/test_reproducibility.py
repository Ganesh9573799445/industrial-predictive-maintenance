
from pathlib import Path
import random
import re

BASE_DIR = Path(__file__).resolve().parents[1]
EXPECTED_SEED = 20261022


def test_project_uses_expected_random_seed():
    config_file = BASE_DIR / "config.py"

    assert config_file.exists()

    config_text = config_file.read_text(encoding="utf-8")

    assert str(EXPECTED_SEED) in config_text


def test_random_seed_produces_repeatable_values():
    first_run = random.Random(EXPECTED_SEED)
    second_run = random.Random(EXPECTED_SEED)

    first_values = [first_run.random() for _ in range(10)]
    second_values = [second_run.random() for _ in range(10)]

    assert first_values == second_values


def test_generator_files_exist():
    generator_dir = BASE_DIR / "src" / "generators"

    required_generators = [
        "master_data.py",
        "telemetry_generator.py",
        "failure_generator.py",
        "maintenance_generator.py",
    ]

    for filename in required_generators:
        assert (generator_dir / filename).exists()
