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
        else:
            self.config = yaml.safe_load(data) or {}

        self.validate()

        # If we are loading from file, we are in a test run, and should write debug info
        if file_path:
            print("Parsed file to config as follows")
            print(self.pretty_format())

    def pretty_format(self):
        # Return a pretty printed version of the config object
        return json.dumps(self.config, indent=4)

    def validate(self):
        # Define the JSON schema for configuration validation
        schema = {
            "type": "object",
            "required": [EMAIL_RECIPS],
            "properties": {
                EMAIL_RECIPS: {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "check": {
                    "type": ["object", "null"],
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
                    "type": ["object", "null"],
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

        # Default the check structure to be present but empty
        try:
            check = self.config["check"]
            if not check:
                raise KeyError
        except KeyError:
            check = {}
            self.config["check"] = check

        # Default the connect structure to be present but empty
        try:
            connect = self.config["connect"]
            if not connect:
                raise KeyError
        except KeyError:
            connect = {}
            self.config["connect"] = connect

        if not "grace_min" in check:
            check["grace_min"] = 15
        if not "ignore_after_min" in check:
            check["ignore_after_min"] = 75
        if not "checkin_grace_min" in connect:
             connect["checkin_grace_min"] = 30
        if not "checkout_grace_min" in connect:
             connect["checkout_grace_min"] = 30
        if not "ignore_after_min" in connect:
            connect["ignore_after_min"] = 75

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