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


    def test_lopa_clears_anuvrtti_context(self):
        source = """तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    वाचम् लोपः ।
    लिखति ।
}
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P1")

    def test_inherited_lopa_must_target_live_state(self):
        source = """तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    लोपः ।
    लोपः ।
}
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P1")

    def test_store_requires_adhikara_even_on_siddha(self):
        source = """तन्त्रशास्त्रम् {
    वाचम् स्थापयति ।
}
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P4")

    def test_inherited_store_uses_live_context(self):
        source = """तन्त्रशास्त्रम् {
    अधिकारः {
        यन्त्र स्थापयति ।
        स्थापयति ।
    }
}
"""
        words = self.compile(source)
        self.assertEqual(words[1], 0x00CC60F0)
        self.assertEqual(words[2], 0x01CC00F0)



if __name__ == "__main__":
    unittest.main()
