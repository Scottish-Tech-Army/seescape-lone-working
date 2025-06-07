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
        Initialize LambdaConfig with configuration data from a file or memory.

        Args:
            file_path (str, optional): Path to YAML configuration file
            data (str, optional): YAML configuration data as a string

        Raises:
            AssertionError: If both or neither file_path and data are provided
            yaml.YAMLError: If YAML parsing fails
            ValueError: If configuration validation fails

        The configuration must contain:
        - At least one of email_recipients_overdue or email_recipients_emergency
        - Optional check and connect sections with timing parameters

        After initialization the following has been done:
        - Configuration has been validated against JSON schema
        - Default values are set for missing optional parameters
        - Both email recipient lists are populated (copying if one is missing)
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
        """
        Validates and normalizes the configuration data.

        Raises:
            ValueError: If configuration fails JSON schema validation or required fields are missing

        The function:
        - Validates against a JSON schema that enforces:
            - Email recipient lists must be non-empty arrays of strings
            - Timing parameters must be non-negative numbers
            - No unexpected configuration sections
        - Sets default values for optional parameters:
            - check.grace_min: 15
            - check.ignore_after_min: 75
            - connect.checkin_grace_min: 15
            - connect.checkout_grace_min: 15
            - connect.ignore_after_min: 75
        - Ensures both email recipient lists exist by copying if one is missing
        """
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
        Retrieves the email recipients list for a specified notification type.

        Args:
            type (str): The type of notification, must be either:
                - "overdue": For missed check-in/out notifications
                - "emergency": For emergency notifications

        Returns:
            list: List of email addresses for the specified notification type

        Raises:
            RuntimeError: If type is not "overdue" or "emergency"
        """
        if type == "overdue":
            return self.config.get(EMAIL_RECIPS_OVERDUE)
        if type == "emergency":
            return self.config.get(EMAIL_RECIPS_EMERGENCY)
        raise RuntimeError(f"Invalid type for get_email_recipients: %s", type)

    def get_app_cfg(self, app_name):
        """
        Retrieves application-specific configuration.

        Args:
            app_name (str): Name of the application (case-insensitive)
                Expected values are "check" or "connect"

        Returns:
            dict: Configuration dictionary for the specified application, containing:
                For "check":
                    - grace_min: Minutes to wait before marking as missed
                    - ignore_after_min: Minutes after which to stop checking
                For "connect":
                    - checkin_grace_min: Minutes grace period for check-ins
                    - checkout_grace_min: Minutes grace period for check-outs
                    - ignore_after_min: Minutes after which to stop checking

        Raises:
            KeyError: If the specified app_name section doesn't exist in config
        """
        return self.config[app_name.lower()]

# For validation purposes, this module must be runnable from the command line.
def main():
    """
    Command-line entry point for configuration validation.

    Usage:
        python cfg_parser.py <filename>

    Args:
        sys.argv[1]: Path to configuration file to validate

    Returns:
        None

    Exits:
        0: If configuration is valid
        1: If incorrect number of arguments
        Raises exception: If configuration is invalid
    """
    if len(sys.argv) != 2:
        print("Usage: python cfg_parser.py <filename>")
        sys.exit(1)
    # Create an instance using command line arguments
    cfg = LambdaConfig(sys.argv[1])
    print("  Validation of config succeeded")

if __name__ == '__main__':
    main()