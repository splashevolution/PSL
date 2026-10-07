import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "utils"))

from paninian_compiler import PaninianFormalCompiler


class CanonicalProgramTests(unittest.TestCase):
    def compile_program(self, name: str):
        source = (ROOT / "programs" / name).read_text(encoding="utf-8")
        return PaninianFormalCompiler().compile_source(source)

    def test_lopa_core_exact_abi(self):
        self.assertEqual(
            self.compile_program("lopa_core.pvm"),
            [0x200530F0, 0x200030F0],
        )

    def test_sandhi_core_exact_abi(self):
        self.assertEqual(
            self.compile_program("sandhi_core.pvm"),
            [
                0x200530F0,
                0x00AA00F0,
                0x00CC60E0,
                0x00CC60F0,
                0x00BB00F0,
            ],
        )

    def test_paribhasha_valid_core_exact_abi(self):
        self.assertEqual(
            self.compile_program("paribhasha_valid_core.pvm"),
            [
                0x200530F0,
                0x210500F0,
                0x200030F0,
                0x00AA00F0,
                0x00CC60F0,
                0x00BB00F0,
            ],
        )

    def test_key_lifecycle_exact_abi(self):
        self.assertEqual(
            self.compile_program("key_lifecycle.pvm"),
            [
                0x200520F0,
                0x00AA00F0,
                0x00CC50F0,
                0x01CC00F0,
                0x00CC70E0,
                0x00CC70F0,
                0x000050F0,
                0x00BB00F0,
                0x200520F0,
            ],
        )

    def test_other_current_scoped_examples_compile(self):
        for name in (
            "anuvritti_core.pvm",
            "adhikara_core.pvm",
            "boot_sequencer.pvm",
            "safety_interlock.pvm",
        ):
            with self.subTest(name=name):
                words = self.compile_program(name)
                self.assertGreater(len(words), 0)


if __name__ == "__main__":
    unittest.main()
