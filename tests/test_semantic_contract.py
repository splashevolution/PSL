import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "utils"))

from paninian_compiler import IRNode, PaninianFormalCompiler, ParibhashaError


class SemanticContractTests(unittest.TestCase):
    def compile(self, source: str):
        return PaninianFormalCompiler().compile_source(source)

    def test_final_ir_snapshot_matches_emitted_words(self):
        compiler = PaninianFormalCompiler()
        source = """तन्त्रशास्त्रम् {
    वाचम् लिखति ।
}
"""
        words = compiler.compile_source(source)
        ir = compiler.get_last_ir()
        self.assertIsInstance(ir, tuple)
        self.assertEqual([node.to_word() for node in ir], words)

    def test_final_ir_unavailable_before_successful_compile(self):
        compiler = PaninianFormalCompiler()
        with self.assertRaises(RuntimeError):
            compiler.get_last_ir()

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



    def test_validator_rejects_ring2_store_even_inside_scope(self):
        compiler = PaninianFormalCompiler()
        nodes = [
            IRNode(
                ring=0, comp=0, opcode=compiler.OPCODE_ADHIKARA_OPEN,
                target=0, cond=0, flags=compiler.FLAG_IMMEDIATE_LOPA,
                source_line=1, source_text="open"
            ),
            IRNode(
                ring=2, comp=0, opcode=compiler.OPCODE_STORE,
                target=0x60, cond=0, flags=compiler.FLAG_IMMEDIATE_LOPA,
                source_line=2, source_text="store"
            ),
            IRNode(
                ring=0, comp=0, opcode=compiler.OPCODE_ADHIKARA_CLOSE,
                target=0, cond=0, flags=compiler.FLAG_IMMEDIATE_LOPA,
                source_line=3, source_text="close"
            ),
        ]
        with self.assertRaises(ParibhashaError) as ctx:
            compiler.validate_ir(nodes)
        self.assertEqual(ctx.exception.rule_id, "P4")



    def test_asiddha_lopa_outside_scope_is_rejected(self):
        source = """सञ्ज्ञा यन्त्र = 0x60 ।
तन्त्रशास्त्रम् {
    यन्त्र लिखति ।
    यन्त्र लोपः ।
}
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P4")

    def test_ring0_siddha_is_rejected(self):
        source = """तन्त्रशास्त्रम् {
    वाग्यन्थ्रैः लिखति ।
}
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P3")

    def test_unclosed_adhikara_is_rejected(self):
        source = """तन्त्रशास्त्रम् {
    अधिकारः {
        यन्त्र स्थापयति ।
"""
        with self.assertRaises(ParibhashaError) as ctx:
            self.compile(source)
        self.assertEqual(ctx.exception.rule_id, "P4")



if __name__ == "__main__":
    unittest.main()
