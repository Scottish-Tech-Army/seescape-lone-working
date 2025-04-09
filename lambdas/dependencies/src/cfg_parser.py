import json
import jsonschema
import logging
import sys
import yaml

logger = logging.getLogger(__name__)

# Do not make the log level DEBUG or it explodes
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


# Key values defined as constants
EMAIL_RECIPS_OVERDUE="email_recipients_overdue"
EMAIL_RECIPS_EMERGENCY="email_recipients_emergency"

class LambdaConfig:
    def __init__(self, file_path=None, data=None):
        """
        Initialize LambdaConfig with a configuration dictionary.

        This is read either from a supplied file path, or from the data in memory.
        """
        assert (file_path is None) != (data is None), "Either file or bucket_name must be provided, but not both"
        self.config = {}

        if file_path:
            logger.info("Opening file %s", file_path)
            with open(file_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            logger.info("Using data in memory")
            self.config = yaml.safe_load(data) or {}

        self.validate()

        logging.info("Loaded config parameters as follows: %s", json.dumps(self.config, indent=4))

    def validate(self):
        # Define the JSON schema for configuration validation
        schema = {
            "type": "object",
            "properties": {
                EMAIL_RECIPS_OVERDUE: {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                EMAIL_RECIPS_EMERGENCY: {
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

        # Check email recipients. We allow you to just specify one array, in which case we make the two the same.
        if EMAIL_RECIPS_EMERGENCY not in self.config and EMAIL_RECIPS_OVERDUE not in self.config:
            raise ValueError(f"At least one of {EMAIL_RECIPS_OVERDUE} and {EMAIL_RECIPS_EMERGENCY} must be set")
        if EMAIL_RECIPS_EMERGENCY not in self.config:
            logger.info("Defaulting emergency recipients to overdue list")
            self.config[EMAIL_RECIPS_EMERGENCY] = self.config[EMAIL_RECIPS_OVERDUE]
        if EMAIL_RECIPS_OVERDUE not in self.config:
            logger.info("Defaulting overdue recipients to emergency list")
            self.config[EMAIL_RECIPS_OVERDUE] = self.config[EMAIL_RECIPS_EMERGENCY]

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
             connect["checkin_grace_min"] = 15
        if not "checkout_grace_min" in connect:
             connect["checkout_grace_min"] = 15
        if not "ignore_after_min" in connect:
            connect["ignore_after_min"] = 75

    def get_email_recipients(self, type):
        """
        Returns the 'email_recipients' field from the configuration dictionary.
        """
        if type == "overdue":
            return self.config.get(EMAIL_RECIPS_OVERDUE)
        if type == "emergency":
            return self.config.get(EMAIL_RECIPS_EMERGENCY)
        raise RuntimeError(f"Invalid type for get_email_recipients: %s", type)

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