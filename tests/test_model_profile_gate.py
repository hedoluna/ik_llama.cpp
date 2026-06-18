import json
import unittest

from scripts.model_profile_gate import ToolCase, evaluate_tool_response


class EvaluateToolResponseTests(unittest.TestCase):
    def test_passes_valid_tool_call_with_matching_arguments(self):
        case = ToolCase(
            id="weather_milan",
            prompt="Che tempo fa a Milano?",
            want_fn="get_weather",
            want_args={"city": "Milano", "unit": "celsius"},
        )
        message = {
            "content": None,
            "tool_calls": [
                {
                    "function": {
                        "name": "get_weather",
                        "arguments": json.dumps({"city": "Milano", "unit": "celsius"}),
                    }
                }
            ],
        }

        result = evaluate_tool_response(case, message, 1.23)

        self.assertEqual(result["verdict"], "PASS")
        self.assertTrue(result["pass"])
        self.assertEqual(result["got_fn"], "get_weather")

    def test_fails_when_no_tool_call_is_returned(self):
        case = ToolCase("weather_milan", "Che tempo fa a Milano?", "get_weather", {"city": "Milano"})

        result = evaluate_tool_response(case, {"content": "Non lo so."}, 0.5)

        self.assertEqual(result["verdict"], "FAIL_NO_TOOLCALL")
        self.assertFalse(result["pass"])

    def test_fails_when_function_name_is_wrong(self):
        case = ToolCase("math_mul", "Quanto fa 47 per 13?", "calculator", {"op": "mul"})
        message = {
            "tool_calls": [
                {"function": {"name": "get_weather", "arguments": json.dumps({"op": "mul"})}}
            ]
        }

        result = evaluate_tool_response(case, message, 0.5)

        self.assertEqual(result["verdict"], "FAIL_NAME")
        self.assertEqual(result["got_fn"], "get_weather")

    def test_fails_when_required_argument_does_not_match(self):
        case = ToolCase("math_mul", "Quanto fa 47 per 13?", "calculator", {"op": "mul", "a": 47})
        message = {
            "tool_calls": [
                {"function": {"name": "calculator", "arguments": json.dumps({"op": "add", "a": 47})}}
            ]
        }

        result = evaluate_tool_response(case, message, 0.5)

        self.assertEqual(result["verdict"], "FAIL_ARGS")
        self.assertEqual(result["missing_or_wrong"], ["op"])

    def test_fails_when_arguments_are_not_valid_json(self):
        case = ToolCase("math_mul", "Quanto fa 47 per 13?", "calculator", {"op": "mul"})
        message = {
            "tool_calls": [
                {"function": {"name": "calculator", "arguments": "{not-json"}}
            ]
        }

        result = evaluate_tool_response(case, message, 0.5)

        self.assertEqual(result["verdict"], "FAIL_BAD_ARGS_JSON")
        self.assertFalse(result["pass"])


if __name__ == "__main__":
    unittest.main()
