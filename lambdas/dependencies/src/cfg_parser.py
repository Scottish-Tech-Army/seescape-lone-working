import sys
import yaml
import json
import jsonschema

# Key values defined as constants
EMAIL_RECIPS="email_recipients"

class LambdaConfig:
    def __init__(self, file_path=None, data=None):
        """
        Initialize LambdaConfig with a configuration dictionary.

        This is read either from a supplied file path, or from the data in memory.
        """
        assert (file_path is None) != (data is None), "Either file or bucket_name must be provided, but not both"
        self.config = {}

        if file_path:
            with open(file_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            # If we are loading from file, we are in a test run
            print("Parsed file to config as follows")
            print(json.dumps(self.config, indent=4))
        else:
            self.config = yaml.safe_load(data) or {}

        self.validate()

    def validate(self):
        # Define the JSON schema for configuration validation
        schema = {
            "type": "object",
            "required": [EMAIL_RECIPS, "check", "connect"],
            "properties": {
                EMAIL_RECIPS: {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "check": {
                    "type": "object",
                    "required": ["grace_min", "ignore_after_min"],
                    "properties": {
                        "grace_min": {
                            "type": "number",
                            "minimum": 0
                        },
                        "ignore_after_min": {
                            "type": "number",
                            "minimum": 0
                        }
                    },
                    "additionalProperties": False
                },
                "connect": {
                    "type": "object",
                    "required": ["checkin_grace_min", "checkout_grace_min", "ignore_after_min"],
                    "properties": {
                        "checkin_grace_min": {
                            "type": "number",
                            "minimum": 0
                        },
                        "checkout_grace_min": {
                            "type": "number",
                            "minimum": 0
                        },
                        "ignore_after_min": {
                            "type": "number",
                            "minimum": 0
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }

        try:
            jsonschema.validate(instance=self.config, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Configuration validation error: {e}")

    def get_email_recipients(self):
        """
        Returns the 'email_recipients' field from the configuration dictionary.
        """
        return self.config.get(EMAIL_RECIPS)

    def get_app_cfg(self, app_name):
        """
        Returns the app specific config blob
        """
        return self.config.get(app_name.lower())

# For validation purposes, this module must be runnable from the command line.
def main():
    if len(sys.argv) != 2:
        print("Usage: python cfg_parser.py <filename>")
        sys.exit(1)
    # Create an instance using command line arguments
    cfg = LambdaConfig(sys.argv[1])
    print("  Validation of config succeeded")

if __name__ == '__main__':
    main()