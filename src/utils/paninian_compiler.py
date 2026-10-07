#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PANINIAN SYSTEM LANGUAGE COMPILER FRONTEND

Builds fixed-width 32-bit PVM instruction words from the formal Karaka/Kriya
subset. The binary image format is big-endian so its byte order is explicit
and independent of the host running the compiler.

Sprint 1:  Linear execution - Siddha/Asiddha/Vrddhi visibility model.
Sprint 2:  Conditional execution - Utsarga / Apavada precedence.
Sprint 3:  Bounded repetition - Avrtti (count encoded in instruction word).
Sprint 4:  Context inheritance - Anuvrtti (target from previous rule).
Sprint 5:  Structured erasure - Lopa (explicit nullification + boundary).
Sprint 6:  Named abstractions - Sanjnaa (compile-time symbol table).
Sprint 7:  Meta-rules - Paribhasha (compile-time constraint enforcement).
Sprint 8:  Semantic IR - Prakriya (explicit intermediate derivation record).
Sprint 9:  Instruction fusion - Sandhi (IR-level atomic pair execution).
Sprint 10: Privilege scope - Adhikara (block-level Ring-0 domain).
Sprint 13: Key lifecycle - P4b Asiddha-outside-scope enforcement.

ABI Word Layout (32-bit, big-endian):
  [31:28] RING_ID        - 0x0 = Ring 0 (Vrddhi), 0x2 = Ring 2 (User)
  [27:24] COMP/COUNT     - 0x0 = explicit, 0x1 = Anuvrtti, N>1 = Avrtti count
  [23:16] OPCODE (Kriya) - 0x00 = Lopa, 0x05 = Write, 0x06 = Read,
                           0xCC = Store, 0xAA = Adhikara-open, 0xBB = Adhikara-close
  [15:08] TARGET         - device address (0x00 for scope sentinels)
  [07:04] FLAGS          - 0xF = Lopa boundary, 0xE = SANDHI-FIRST
  [03:00] COND           - 0x0 = Unconditional, 0x1 = Utsarga, 0x2 = Apavada

Paribhasha constraints (Sprint 7+):
  P1: Anuvrtti-at-start  - compressed instruction cannot be first.
  P2: Lopa-on-unwritten  - Lopa cannot erase a target never written.
  P3: Vrddhi-on-Siddha   - Ring 0 invalid on Siddha target (< 0x50).
  P4: Ring0-outside-scope - Ring 0 instruction outside an Adhikara block.
  P4b: Asiddha-outside-scope - Store/Lopa on Asiddha outside Adhikara.

Prakriya IR pipeline (Sprint 8+, Sprint 10 complete):
  _parse_sanjnaa(code)        -- first pass: symbol table
  _parse_adhikara(code)       -- first pass: scope depth tracking
  per line: _build_ir_node()  -- AST -> IRNode
  sandhi_pass(ir_list)        -- IR transform: mark fused pairs
  validate_ir(ir_list)        -- Paribhasha checks P1-P4
  check_lowering_invariants() -- L1/L2 safety
  emit_from_ir(ir_list)       -- IR -> 32-bit words

Lowering invariants:
  L1: Every IRNode lowers to exactly one deterministic 32-bit word.
  L2: No IR transform may introduce a Paribhasha violation post-validation.

Safeguard rule:
  Every concept must change compiler behavior, change emitted ABI,
  change runtime behavior, or reject illegal programs. If not -- cut it.
"""

import re
import struct
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Paribhasha exception
# ---------------------------------------------------------------------------

class ParibhashaError(Exception):
    """
    Raised when a PSL program violates a named Paribhasha meta-rule.
    The violation is caught at the IR validation pass -- no binary is emitted.
    """
    def __init__(self, rule_id, rule_name, line_number, line_text, detail):
        self.rule_id     = rule_id
        self.rule_name   = rule_name
        self.line_number = line_number
        self.line_text   = line_text
        self.detail      = detail
        super().__init__(
            "[Paribhasha %s: %s] line %d: %r\n  Source: %r"
            % (rule_id, rule_name, line_number, detail, line_text)
        )


# ---------------------------------------------------------------------------
# Sandhi exception
# ---------------------------------------------------------------------------

class SandhiError(Exception):
    """
    Raised when a declared Sandhi fusion violates a compatibility rule.
    """
    def __init__(self, rule_id, rule_name, line_a, line_b, detail):
        self.rule_id   = rule_id
        self.rule_name = rule_name
        self.line_a    = line_a
        self.line_b    = line_b
        self.detail    = detail
        super().__init__(
            "[Sandhi %s: %s] lines %d-%d: %r"
            % (rule_id, rule_name, line_a, line_b, detail)
        )


# ---------------------------------------------------------------------------
# Prakriya IR Node (Sprint 8+)
# ---------------------------------------------------------------------------

@dataclass
class IRNode:
    """
    Prakriya -- the explicit intermediate derivation record.
    One IRNode per executable instruction (including scope sentinels).
    """
    ring:         int
    comp:         int
    opcode:       int
    target:       Optional[int]
    cond:         int
    flags:        int
    source_line:  int
    source_text:  str
    constraints:  List[str] = field(default_factory=list)
    region:       Optional[str] = None
    sandhi_fused: bool = False    # True if first of a Sandhi pair
    in_adhikara:  bool = False    # True if emitted inside an Adhikara block

    def to_word(self) -> int:
        """Pack this IRNode into a 32-bit ABI word."""
        t     = self.target if self.target is not None else 0x00
        flags = 0x0E if self.sandhi_fused else self.flags
        return (
              (self.ring   << 28)
            | (self.comp   << 24)
            | (self.opcode << 16)
            | (t           <<  8)
            | ((flags & 0x0F) << 4)
            | (self.cond   & 0x0F)
        )

    def describe(self) -> str:
        """Human-readable one-line summary for IR inspection."""
        t_str  = ("0x%02X" % self.target) if self.target is not None else "inherited"
        r_str  = "Ring%d" % self.ring
        region = (" [%s]"        % self.region) if self.region       else ""
        sandhi = " [SANDHI-FIRST]" if self.sandhi_fused              else ""
        scope  = " [IN-ADHIKARA]" if self.in_adhikara                else ""
        checks = " ".join(self.constraints) if self.constraints      else "unchecked"
        return (
            "  line%-3d  ring=%-5s  op=0x%02X  target=%-9s  comp=0x%X  "
            "cond=0x%X  word=0x%08X%s%s%s  {%s}"
            % (self.source_line, r_str, self.opcode, t_str, self.comp,
               self.cond, self.to_word(), region, sandhi, scope, checks)
        )


# ---------------------------------------------------------------------------
# Token / AST
# ---------------------------------------------------------------------------

class Token:
    def __init__(self, type_, value):
        self.type  = type_
        self.value = value


class ASTNode:
    def __init__(self, type_, children=None, metadata=None):
        self.type     = type_
        self.children = children if children else []
        self.metadata = metadata if metadata else {}


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------

class PaninianFormalCompiler:
    DEFAULT_RING        = 0x02
    FLAG_IMMEDIATE_LOPA = 0x0F
    FLAG_SANDHI_FUSED   = 0x0E   # first word of a Sandhi-fused pair
    COMP_EXPLICIT       = 0x0
    COMP_ANUVRTTI       = 0x1

    COND_UNCONDITIONAL  = 0x0
    COND_UTSARGA        = 0x1
    COND_APAVADA        = 0x2

    ASIDDHA_BASE        = 0x50

    # Adhikara scope sentinel opcodes (Sprint 10)
    OPCODE_ADHIKARA_OPEN  = 0xAA
    OPCODE_ADHIKARA_CLOSE = 0xBB

    # Named opcode constants (Sprint 13 -- used in P4b validation)
    OPCODE_LOPA  = 0x00
    OPCODE_STORE = 0xCC

    DEVA_DIGITS = {
        "1": 1, "2": 2, "3": 3, "4": 4,
        "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
        "1": 1, "2": 2, "3": 3, "4": 4,
        "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    }

    SANJNAA_KEYWORD   = "सञ्ज्ञा"
    TANTRA_KEYWORD    = "तन्त्रशास्त्रम्"
    SANDHI_KEYWORD    = "सन्धिः"
    ADHIKARA_KEYWORD  = "अधिकारः"

    def __init__(self):
        self.kriya_lexicon = {
            "लिखति":    0x05,
            "शृणोति":   0x06,
            "स्थापयति": 0xCC,
            "लोपः":     0x00,
        }
        self.karaka_lexicon = {
            "वाचम्":    {"addr": 0x30, "role": "KARMAN"},
            "श्रोत्रम्": {"addr": 0x50, "role": "KARMAN"},
            "श्रोत्रात्": {"addr": 0x50, "role": "APADANA"},
            "यन्त्रम्":  {"addr": 0x60, "role": "KARMAN"},
            "यन्त्र":    {"addr": 0x60, "role": "KARMAN"},
            "यन्त्रै":   {"addr": 0x60, "role": "VRDDHI_RING_0"},
            "वाग्यन्थ्रैः": {"addr": 0x30, "role": "VRDDHI_RING_0"},
        }
        self.condition_lexicon = {
            "उत्सर्गः": self.COND_UTSARGA,
            "अपवादः":  self.COND_APAVADA,
        }
        self.avrtti_keyword = "आवृत्तिः"
        self.sanjnaa_table  = {}

    # ------------------------------------------------------------------
    # Sanjnaa - first-pass symbol extraction (Sprint 6)
    # ------------------------------------------------------------------

    def _parse_sanjnaa(self, code):
        self.sanjnaa_table = {}
        for raw_line in code.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line.startswith(self.SANJNAA_KEYWORD):
                continue
            body = line[len(self.SANJNAA_KEYWORD):].strip()
            body = re.sub(r"[।.]", "", body).strip()
            if "=" not in body:
                raise SyntaxError("Malformed Sanjnaa declaration: %r" % raw_line)
            name_part, addr_part = body.split("=", 1)
            name     = name_part.strip()
            addr_str = addr_part.strip()
            try:
                addr = int(addr_str, 16)
            except ValueError:
                raise SyntaxError(
                    "Sanjnaa address must be hex (e.g. 0x30): %r" % addr_str
                )
            if not name:
                raise SyntaxError("Sanjnaa name is empty in: %r" % raw_line)
            self.sanjnaa_table[name] = {"addr": addr, "role": "KARMAN"}

    def _resolve_karaka(self, token_value):
        if token_value in self.karaka_lexicon:
            return self.karaka_lexicon[token_value]
        if token_value in self.sanjnaa_table:
            return self.sanjnaa_table[token_value]
        return None

    # ------------------------------------------------------------------
    # Lexer / Parser
    # ------------------------------------------------------------------

    def lex(self, code):
        raw_tokens = re.split(r"\s+", code.strip())
        tokens = []
        for raw_token in raw_tokens:
            clean = re.sub(r"[।.]", "", raw_token)
            if not clean:
                continue
            if clean == self.SANDHI_KEYWORD:
                tokens.append(Token("SANDHI", clean))
            elif clean == self.ADHIKARA_KEYWORD:
                tokens.append(Token("ADHIKARA_OPEN", clean))
            elif clean == self.avrtti_keyword:
                tokens.append(Token("AVRTTI", clean))
            elif clean in self.DEVA_DIGITS:
                tokens.append(Token("DIGIT", clean))
            elif clean in self.condition_lexicon:
                tokens.append(Token("CONDITION", clean))
            elif clean in self.kriya_lexicon:
                tokens.append(Token("KRIYA", clean))
            else:
                meta = self._resolve_karaka(clean)
                if meta is not None:
                    tokens.append(Token("KARAKA", clean))
        return tokens

    def parse(self, tokens):
        root = ASTNode("SUTRA_STREAM")
        current_statement = ASTNode("STATEMENT")
        for token in tokens:
            if token.type == "SANDHI":
                current_statement.children.append(
                    ASTNode("SANDHI_NODE", metadata={"lexeme": token.value}))
                root.children.append(current_statement)
                current_statement = ASTNode("STATEMENT")
            elif token.type == "ADHIKARA_OPEN":
                current_statement.children.append(
                    ASTNode("ADHIKARA_NODE", metadata={"lexeme": token.value}))
                root.children.append(current_statement)
                current_statement = ASTNode("STATEMENT")
            elif token.type == "AVRTTI":
                current_statement.children.append(
                    ASTNode("AVRTTI_NODE", metadata={"lexeme": token.value}))
            elif token.type == "DIGIT":
                current_statement.children.append(
                    ASTNode("DIGIT_NODE",
                            metadata={"count": self.DEVA_DIGITS[token.value]}))
            elif token.type == "CONDITION":
                current_statement.children.append(
                    ASTNode("CONDITION_NODE",
                            metadata={"cond": self.condition_lexicon[token.value],
                                      "lexeme": token.value}))
            elif token.type == "KARAKA":
                meta = self._resolve_karaka(token.value)
                current_statement.children.append(
                    ASTNode("KARAKA_NODE", metadata=meta))
            elif token.type == "KRIYA":
                current_statement.children.append(
                    ASTNode("KRIYA_NODE",
                            metadata={"opcode": self.kriya_lexicon[token.value],
                                      "lexeme": token.value}))
                root.children.append(current_statement)
                current_statement = ASTNode("STATEMENT")
        return root

    # ------------------------------------------------------------------
    # Sprint 8: Prakriya -- AST -> IRNode
    # ------------------------------------------------------------------

    def _build_ir_node(self, ast, source_line, source_text, prev_target=None,
                       adhikara_depth=0):
        """
        Convert a single-statement AST into one or more IRNodes.
        adhikara_depth: current scope nesting level at this line.
        """
        if not ast.children:
            return []

        # Sandhi directive
        if (len(ast.children) == 1
                and len(ast.children[0].children) == 1
                and ast.children[0].children[0].type == "SANDHI_NODE"):
            return [IRNode(
                ring=0, comp=0, opcode=0xFF, target=None,
                cond=0, flags=0, source_line=source_line,
                source_text=source_text, constraints=["SANDHI-sentinel"],
                region=None,
            )]

        # Adhikara open/close directives
        if (len(ast.children) == 1
                and len(ast.children[0].children) == 1
                and ast.children[0].children[0].type == "ADHIKARA_NODE"):
            return [IRNode(
                ring=0, comp=0, opcode=self.OPCODE_ADHIKARA_OPEN, target=0x00,
                cond=0, flags=self.FLAG_IMMEDIATE_LOPA,
                source_line=source_line, source_text=source_text,
                constraints=["ADHIKARA-open"],
                region=None, in_adhikara=False,
            )]

        ir_nodes = []
        for statement in ast.children:
            ring_id     = self.DEFAULT_RING
            count       = 0x0
            opcode      = 0x00
            target_addr = None
            cond        = self.COND_UNCONDITIONAL
            has_avrtti  = False

            for node in statement.children:
                if node.type == "AVRTTI_NODE":
                    has_avrtti = True
                elif node.type == "DIGIT_NODE":
                    count = node.metadata["count"] & 0x0F
                elif node.type == "CONDITION_NODE":
                    cond = node.metadata["cond"]
                elif node.type == "KARAKA_NODE":
                    target_addr = node.metadata["addr"]
                    if node.metadata.get("role") == "VRDDHI_RING_0":
                        ring_id = 0x00
                elif node.type == "KRIYA_NODE":
                    opcode = node.metadata["opcode"]

            if has_avrtti and count == 0:
                count = 1

            # Inside an Adhikara block, Store and Lopa are implicitly Ring 0.
            # Lopa (structured erasure) of an Asiddha register requires the same
            # privilege as writing to it -- zeroization is a privileged operation.
            if adhikara_depth > 0 and opcode in (0xCC, 0x00) and ring_id == self.DEFAULT_RING:
                ring_id = 0x00

            if target_addr is None:
                comp = self.COMP_ANUVRTTI
                resolved_target = None
            else:
                comp = count if has_avrtti else self.COMP_EXPLICIT
                resolved_target = target_addr

            if resolved_target is not None:
                region = "ASIDDHA" if resolved_target >= self.ASIDDHA_BASE else "SIDDHA"
            else:
                region = None

            ir_nodes.append(IRNode(
                ring        = ring_id,
                comp        = comp,
                opcode      = opcode,
                target      = resolved_target,
                cond        = cond,
                flags       = self.FLAG_IMMEDIATE_LOPA,
                source_line = source_line,
                source_text = source_text,
                constraints = [],
                region      = region,
                in_adhikara = adhikara_depth > 0,
            ))

        return ir_nodes

    # ------------------------------------------------------------------
    # Sprint 8: IR validation -- Paribhasha checks P1-P4
    # ------------------------------------------------------------------

    def validate_ir(self, ir_list):
        """
        Validate the canonical PSL semantic contract.

        State tracked by this pass:
          * written_targets: targets with a live write
          * adhikara_depth: lexical privilege scope depth
          * context_target: target available to Anuvrtti

        Lopa is a structural boundary: after a successful Lopa, context_target
        is cleared. Therefore an immediately following Anuvrtti is rejected at
        compile time rather than relying on firmware-specific behaviour.
        """
        written_targets = set()
        adhikara_depth = 0
        context_target = None

        for node in ir_list:
            if node.opcode == self.OPCODE_ADHIKARA_OPEN:
                adhikara_depth += 1
                node.constraints.append("ADHIKARA-open")
                continue

            if node.opcode == self.OPCODE_ADHIKARA_CLOSE:
                if adhikara_depth == 0:
                    raise ParibhashaError(
                        "P4", "Adhikara-close-without-open",
                        node.source_line, node.source_text,
                        "Adhikara close encountered with no active scope"
                    )
                adhikara_depth -= 1
                node.constraints.append("ADHIKARA-close")
                continue

            # Resolve the semantic target used by legality checks.  The ABI
            # still encodes TARGET=0 for Anuvrtti; this value exists only in
            # the compiler's validation state.
            if node.comp == self.COMP_ANUVRTTI:
                if context_target is None:
                    raise ParibhashaError(
                        "P1", "Anuvrtti-without-context",
                        node.source_line, node.source_text,
                        "Compressed instruction has no live target to inherit; "
                        "program start and Lopa boundaries clear inheritance context"
                    )
                effective_target = context_target
            else:
                effective_target = node.target

            node.constraints.append("P1-ok")

            # P2: every Lopa, explicit or inherited, must erase live state.
            if node.opcode == self.OPCODE_LOPA:
                if effective_target is None or effective_target not in written_targets:
                    raise ParibhashaError(
                        "P2", "Lopa-on-unwritten",
                        node.source_line, node.source_text,
                        "Lopa targets 0x%02X which has no live prior write "
                        "(written so far: %s)" % (
                            effective_target if effective_target is not None else 0,
                            sorted("0x%02X" % t for t in written_targets) or ["none"]
                        )
                    )
            node.constraints.append("P2-ok")

            # P3: privileged instructions may only resolve to Asiddha targets.
            # Unlike the historical implementation, this check also covers an
            # inherited target because its effective address is now known here.
            if node.ring == 0x00 and effective_target is not None:
                if effective_target < self.ASIDDHA_BASE:
                    raise ParibhashaError(
                        "P3", "Vrddhi-on-Siddha",
                        node.source_line, node.source_text,
                        "Ring 0 (Vrddhi) resolves to Siddha target 0x%02X "
                        "(Siddha region < 0x%02X)" % (
                            effective_target, self.ASIDDHA_BASE
                        )
                    )
            node.constraints.append("P3-ok")

            # P4: every Ring-0 instruction must be lexically scoped.
            if node.ring == 0x00 and adhikara_depth == 0:
                raise ParibhashaError(
                    "P4", "Ring0-outside-scope",
                    node.source_line, node.source_text,
                    "Ring 0 instruction outside an Adhikara scope"
                )

            # Store is PSL's privileged shadow-write operation and therefore
            # always requires an Adhikara scope.  Lopa requires privilege only
            # when its resolved target is Asiddha.
            if node.opcode == self.OPCODE_STORE:
                if adhikara_depth == 0:
                    raise ParibhashaError(
                        "P4", "Store-outside-scope",
                        node.source_line, node.source_text,
                        "Store is a privileged operation and requires Adhikara"
                    )
                if node.ring != 0x00:
                    raise ParibhashaError(
                        "P4", "Store-without-Ring0",
                        node.source_line, node.source_text,
                        "Store inside Adhikara must carry Ring 0"
                    )

            if (node.opcode == self.OPCODE_LOPA
                    and effective_target is not None
                    and effective_target >= self.ASIDDHA_BASE):
                if adhikara_depth == 0:
                    raise ParibhashaError(
                        "P4", "Asiddha-lopa-outside-scope",
                        node.source_line, node.source_text,
                        "Lopa on an Asiddha target requires Adhikara"
                    )
                if node.ring != 0x00:
                    raise ParibhashaError(
                        "P4", "Asiddha-lopa-without-Ring0",
                        node.source_line, node.source_text,
                        "Lopa on an Asiddha target must carry Ring 0"
                    )

            node.constraints.append("P4-ok")

            # State transition for the validator.  Inherited writes/stores act
            # on the resolved target just like explicit ones.
            if (node.opcode in (0x05, self.OPCODE_STORE)
                    and effective_target is not None):
                written_targets.add(effective_target)
            elif node.opcode == self.OPCODE_LOPA and effective_target is not None:
                written_targets.discard(effective_target)

            # Explicit statements establish inheritance context.  Lopa,
            # explicit or inherited, is a boundary and clears it.
            if node.opcode == self.OPCODE_LOPA:
                context_target = None
            elif node.comp != self.COMP_ANUVRTTI and node.target is not None:
                context_target = node.target

        if adhikara_depth != 0:
            raise ParibhashaError(
                "P4", "Unclosed-Adhikara",
                ir_list[-1].source_line if ir_list else 0,
                ir_list[-1].source_text if ir_list else "<EOF>",
                "Compilation ended with %d unclosed Adhikara scope(s)"
                % adhikara_depth
            )

    # ------------------------------------------------------------------
    # Sprint 8: Lowering invariants
    # ------------------------------------------------------------------

    def check_lowering_invariants(self, ir_list):
        """
        L1: Deterministic lowering -- every IRNode to one stable 32-bit word.
        L2: No IR transform introduces P1 or P3 post-validation.
        """
        first_real = True
        for i, node in enumerate(ir_list):
            if node.opcode in (self.OPCODE_ADHIKARA_OPEN,
                               self.OPCODE_ADHIKARA_CLOSE):
                continue  # sentinels bypass invariants

            word_a = node.to_word()
            word_b = node.to_word()
            assert word_a == word_b, (
                "L1 violation: IRNode at line %d non-deterministic "
                "(0x%08X != 0x%08X)" % (node.source_line, word_a, word_b)
            )
            assert 0 <= word_a <= 0xFFFFFFFF, (
                "L1 violation: IRNode at line %d out-of-range "
                "0x%X" % (node.source_line, word_a)
            )
            if node.comp == self.COMP_ANUVRTTI and first_real:
                raise AssertionError(
                    "L2 violation (P1): IR transform introduced Anuvrtti-at-start "
                    "at line %d" % node.source_line
                )
            if node.ring == 0x00 and node.target is not None:
                if node.target < self.ASIDDHA_BASE:
                    raise AssertionError(
                        "L2 violation (P3): IR transform introduced Ring-0 on "
                        "Siddha target 0x%02X at line %d" % (
                            node.target, node.source_line)
                    )
            first_real = False

    # ------------------------------------------------------------------
    # Sprint 8: Binary emission from IR
    # ------------------------------------------------------------------

    def emit_from_ir(self, ir_list):
        """
        Convert a validated IR list into 32-bit ABI words.
        This is the only path to binary -- AST is never packed directly.
        """
        return [node.to_word() for node in ir_list]

    def print_ir(self, source_or_ir, label="Prakriya IR"):
        """Print the Prakriya IR. Accepts source string or IR list."""
        if isinstance(source_or_ir, str):
            self._parse_sanjnaa(source_or_ir)
            ir_list = []
            prev_target    = 0x00
            adhikara_depth = 0
            for line_number, raw_line in enumerate(source_or_ir.splitlines(), 1):
                statement = raw_line.split("#", 1)[0].strip()
                if (not statement
                        or statement == "{"
                        or statement.startswith(self.TANTRA_KEYWORD)
                        or statement.startswith(self.SANJNAA_KEYWORD)):
                    continue
                if statement == "}":
                    if adhikara_depth > 0:
                        ir_list.append(IRNode(
                            ring=0, comp=0, opcode=self.OPCODE_ADHIKARA_CLOSE,
                            target=0x00, cond=0, flags=self.FLAG_IMMEDIATE_LOPA,
                            source_line=line_number, source_text=statement,
                            constraints=["ADHIKARA-close"], region=None,
                        ))
                        adhikara_depth -= 1
                    continue
                stmt_ast  = self.parse(self.lex(statement))
                new_nodes = self._build_ir_node(
                    stmt_ast, line_number, statement,
                    prev_target=prev_target, adhikara_depth=adhikara_depth
                )
                for node in new_nodes:
                    if node.opcode == self.OPCODE_ADHIKARA_OPEN:
                        adhikara_depth += 1
                    elif node.comp != self.COMP_ANUVRTTI and node.target is not None:
                        prev_target = node.target
                ir_list.extend(new_nodes)
            ir_list = self.sandhi_pass(ir_list)
        else:
            ir_list = source_or_ir
        print("[%s] %d instruction(s):" % (label, len(ir_list)))
        for node in ir_list:
            print(node.describe())

    # ------------------------------------------------------------------
    # Public compilation entry point
    # ------------------------------------------------------------------

    def compile_source(self, code, enforce_paribhasha=True, print_ir=False):
        """
        Compile PSL source to a list of 32-bit ABI words.

        Pipeline (Sprint 10 complete):
          1. _parse_sanjnaa(code)           -- extract symbol table
          2. per line: _build_ir_node()     -- AST -> IRNode
             (tracks adhikara_depth; emits OPEN/CLOSE sentinels)
          3. sandhi_pass(ir_list)           -- mark fused pairs
          4. validate_ir(ir_list)           -- P1/P2/P3/P4/P4b checks
          5. check_lowering_invariants()    -- L1/L2 assertions
          6. emit_from_ir(ir_list)          -- IR -> 32-bit words
        """
        self._parse_sanjnaa(code)

        ir_list        = []
        prev_target    = 0x00
        adhikara_depth = 0

        for line_number, raw_line in enumerate(code.splitlines(), 1):
            statement = raw_line.split("#", 1)[0].strip()

            if (not statement
                    or statement == "{"
                    or statement.startswith(self.TANTRA_KEYWORD)
                    or statement.startswith(self.SANJNAA_KEYWORD)):
                continue

            if statement == "}":
                if adhikara_depth > 0:
                    ir_list.append(IRNode(
                        ring=0, comp=0, opcode=self.OPCODE_ADHIKARA_CLOSE,
                        target=0x00, cond=0, flags=self.FLAG_IMMEDIATE_LOPA,
                        source_line=line_number, source_text=statement,
                        constraints=["ADHIKARA-close"], region=None,
                    ))
                    adhikara_depth -= 1
                continue

            stmt_ast  = self.parse(self.lex(statement))
            new_nodes = self._build_ir_node(
                stmt_ast, line_number, statement,
                prev_target=prev_target, adhikara_depth=adhikara_depth
            )

            if not new_nodes:
                raise SyntaxError(
                    "Unsupported executable statement at line %d: %s"
                    % (line_number, statement)
                )

            for node in new_nodes:
                if node.opcode == self.OPCODE_ADHIKARA_OPEN:
                    adhikara_depth += 1
                elif node.comp != self.COMP_ANUVRTTI and node.target is not None:
                    prev_target = node.target

            ir_list.extend(new_nodes)

        self.sandhi_pass(ir_list)

        if enforce_paribhasha:
            self.validate_ir(ir_list)

        self.check_lowering_invariants(ir_list)

        if print_ir:
            self.print_ir(ir_list)

        # Expose the final IR for external inspection (Sprint 14 verified chain).
        # The list is stored after all passes (Sandhi, Paribhasha, L1/L2 checks)
        # so it reflects exactly what will be lowered.
        self._last_ir = ir_list

        # Expose the final IR for external inspection (Sprint 14 verified chain).
        # Stored after all passes so it reflects exactly what will be lowered.
        self._last_ir = ir_list

        return self.emit_from_ir(ir_list)

    # ------------------------------------------------------------------
    # Sprint 9: Sandhi -- IR-level fusion transform
    # ------------------------------------------------------------------

    def sandhi_pass(self, ir_list):
        """
        Apply Sandhi fusion. Scans for sentinel nodes (opcode=0xFF),
        validates pairs against S1-S5, marks first as sandhi_fused,
        removes sentinel. Returns ir_list for chaining.
        """
        sentinel_indices = [
            i for i, n in enumerate(ir_list) if n.opcode == 0xFF
        ]

        for si in reversed(sentinel_indices):
            if si == 0 or si >= len(ir_list) - 1:
                marker = ir_list[si]
                raise SandhiError(
                    "S0", "Sandhi-at-boundary",
                    marker.source_line, marker.source_line,
                    "Sandhi directive has no valid instruction pair"
                )
            node_a = ir_list[si - 1]
            node_b = ir_list[si + 1]

            if node_a.opcode not in (0x05, 0xCC) or node_b.opcode not in (0x05, 0xCC):
                raise SandhiError(
                    "S1", "Sandhi-non-write",
                    node_a.source_line, node_b.source_line,
                    "Sandhi requires both instructions to be write-class "
                    "(Write 0x05 or Store 0xCC); Lopa cannot be fused"
                )

            if node_a.target != node_b.target or node_a.target is None:
                raise SandhiError(
                    "S2", "Sandhi-target-mismatch",
                    node_a.source_line, node_b.source_line,
                    "Sandhi requires both instructions to target the same "
                    "device address (got 0x%02X and %s)" % (
                        node_a.target or 0,
                        "0x%02X" % node_b.target if node_b.target else "inherited"
                    )
                )

            if node_a.comp == self.COMP_ANUVRTTI:
                raise SandhiError(
                    "S3", "Sandhi-anuvrtti-first",
                    node_a.source_line, node_b.source_line,
                    "Sandhi first instruction must be explicit (not Anuvrtti)"
                )

            if node_a.ring != node_b.ring:
                raise SandhiError(
                    "S4", "Sandhi-ring-mismatch",
                    node_a.source_line, node_b.source_line,
                    "Sandhi requires both instructions in the same ring "
                    "(got Ring%d and Ring%d)" % (node_a.ring, node_b.ring)
                )

            prior_nodes = ir_list[:si]
            last_lopa_line = None
            last_write_line = None
            for prior in prior_nodes:
                if prior.target == node_a.target:
                    if prior.opcode == 0x00:
                        last_lopa_line = prior.source_line
                        last_write_line = None
                    elif prior.opcode in (0x05, 0xCC):
                        last_write_line = prior.source_line
            if last_lopa_line is not None and last_write_line is None:
                raise SandhiError(
                    "S5", "Sandhi-after-lopa",
                    node_a.source_line, node_b.source_line,
                    "Sandhi on target 0x%02X which was erased by Lopa "
                    "at line %d with no intervening write; "
                    "fusing after erasure is incoherent" % (
                        node_a.target, last_lopa_line)
                )

            node_a.sandhi_fused = True
            node_a.constraints.append("SANDHI-ok")
            node_b.constraints.append("SANDHI-pair")
            ir_list.pop(si)

        return ir_list

    # ------------------------------------------------------------------
    # Legacy helpers (kept for backward compatibility)
    # ------------------------------------------------------------------

    def emit_words(self, ast, prev_target=None):
        """Legacy direct emitter -- still works, bypasses IR."""
        words = []
        for statement in ast.children:
            ring_id     = self.DEFAULT_RING
            count       = 0x0
            opcode      = 0x00
            target_addr = None
            cond        = self.COND_UNCONDITIONAL
            has_avrtti  = False
            for node in statement.children:
                if node.type == "AVRTTI_NODE":
                    has_avrtti = True
                elif node.type == "DIGIT_NODE":
                    count = node.metadata["count"] & 0x0F
                elif node.type == "CONDITION_NODE":
                    cond = node.metadata["cond"]
                elif node.type == "KARAKA_NODE":
                    target_addr = node.metadata["addr"]
                    if node.metadata.get("role") == "VRDDHI_RING_0":
                        ring_id = 0x00
                elif node.type == "KRIYA_NODE":
                    opcode = node.metadata["opcode"]
            if has_avrtti and count == 0:
                count = 1
            if target_addr is None:
                compression = self.COMP_ANUVRTTI
                target_addr = 0x00
            else:
                compression = count if has_avrtti else self.COMP_EXPLICIT
                prev_target = target_addr
            flags_and_cond = ((self.FLAG_IMMEDIATE_LOPA & 0x0F) << 4) | (cond & 0x0F)
            words.append(
                  (ring_id     << 28)
                | (compression << 24)
                | (opcode      << 16)
                | (target_addr <<  8)
                | flags_and_cond
            )
        return words

    def emit_bytecode(self, ast):
        return "\n".join("ABI_EMIT 0x%08X" % w for w in self.emit_words(ast))

   