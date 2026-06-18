import unittest

from scripts.opencode_profile_gate import (
    evaluate_task,
    extract_text_from_opencode_lines,
)


class ExtractTextFromOpenCodeLinesTests(unittest.TestCase):
    def test_extracts_text_events_from_json_lines(self):
        lines = [
            '{"type":"text","part":{"text":"hello "}}',
            '{"type":"text","part":{"text":"world"}}',
            '{"type":"step_finish","part":{"tokens":{"input":1,"output":2,"total":3}}}',
        ]

        result = extract_text_from_opencode_lines(lines)

        self.assertEqual(result["text"], "hello world")
        self.assertEqual(result["tokens"], {"input": 1, "output": 2, "total": 3})

    def test_keeps_non_json_lines_as_text(self):
        result = extract_text_from_opencode_lines(["plain output"])

        self.assertEqual(result["text"], "plain output")
        self.assertIsNone(result["tokens"])


class EvaluateTaskTests(unittest.TestCase):
    def test_explain_bug_passes_when_cache_user_name_bug_is_identified(self):
        output = "Il bug e che cache[id] salva user.name invece dell'intero user object. Fix: cache[id] = user."

        result = evaluate_task("explain-bug", output)

        self.assertTrue(result["pass"])
        self.assertEqual(result["verdict"], "PASS")

    def test_write_patch_passes_for_null_safe_slugify(self):
        output = """
        export function slugify(input?: string | null): string {
          if (!input) return '';
          return input.trim().toLowerCase().replaceAll(' ', '-');
        }
        """

        result = evaluate_task("write-patch", output)

        self.assertTrue(result["pass"])

    def test_review_passes_when_dangling_cstr_lifetime_is_called_out(self):
        output = "Rischio principale: dangling pointer, perche s.c_str() punta al buffer di una std::string locale."

        result = evaluate_task("review", output)

        self.assertTrue(result["pass"])

    def test_unknown_task_fails_closed(self):
        result = evaluate_task("unknown", "anything")

        self.assertFalse(result["pass"])
        self.assertEqual(result["verdict"], "FAIL_UNKNOWN_TASK")


if __name__ == "__main__":
    unittest.main()
