import sys
import yaml

# Key values defined as constants
EMAIL_RECIPS="email_recipients"

class LambdaConfig:
    def __init__(self, file_path=None, bucket_name=None):
        """
        Initialize LambdaConfig with a configuration dictionary.

        This is read either from a supplied file path, or from the path a supplied s3 bucket.
        """
        assert (file_path is None) != (bucket_name is None), "Either file or bucket_name must be provided, but not both"
        self.config = {}

        if file_path:
            with open(file_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}

        if bucket_name:
            # Imports in code are ugly, but this way the import is only done when needed.
            import boto3
            s3 = boto3.client('s3')
            response = s3.get_object(Bucket=bucket_name, Key='config')
            self.config = yaml.safe_load(response['Body'].read()) or {}
            assert self.config, "No configuration found: S3 object {bucket_name}/config is empty or invalid YAML"

        self.validate()

    def validate(self):
        # We assert that the data is correct; if passed invalid data we are just doomed.
        assert EMAIL_RECIPS in self.config, f"Configuration invalid: required key '{EMAIL_RECIPS}' is missing."
        assert isinstance(self.config.get(EMAIL_RECIPS), list) and all(isinstance(item, str) for item in self.config.get(EMAIL_RECIPS)), \
            f"Configuration invalid: '{EMAIL_RECIPS}' must be a list of strings."

    def get_email_recipients(self):
        """
        Returns the 'email_recipients' field from the configuration dictionary.
        """
        return self.config.get(EMAIL_RECIPS)

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