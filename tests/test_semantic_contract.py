import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "utils"))

from paninian_compiler import PaninianFormalCompiler, ParibhashaError


class SemanticContractTests(unittest.TestCase):
    def compile(self, source: str):
        return PaninianFormalCompiler().compile_source(source)

    def test_ring2_write_to_asiddha_remains_legal(self):
        source = """तन्त्रशास्त्रम् {
    यन्त्र लिखति ।
}
"""
        words = self.compile(source)
        self.assertEqual(words, [0x200560F0])

    def test_explicit_lopa_consumes_written_state(self):
        source = """तन्त्रशास्त्रम् {
    अधिकारः {
        यन्त्र स्थापयति ।
        यन्त्र लोपः ।
        यन्त्र लोपः ।
    }
}
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P2")

    def test_write_reestablishes_state_after_lopa(self):
        source = """तन्त्रशास्त्रम् {
    अधिकारः {
        यन्त्र स्थापयति ।
        यन्त्र लोपः ।
        यन्त्र स्थापयति ।
        यन्त्र लोपः ।
    }
}
"""
        words = self.compile(source)
        self.assertGreater(len(words), 0)


if __name__ == "__main__":
    unittest.main()
