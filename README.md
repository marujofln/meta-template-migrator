# WhatsApp Template Migrator

A Python script to migrate WhatsApp Business API templates from one account to another. This tool helps you transfer message templates between different WhatsApp Business Accounts (WABA) while maintaining data integrity and providing comprehensive validation.

## Features

- 🔄 **Template Migration**: Copy templates from source to destination WABA
- ✅ **Validation**: Comprehensive template validation before migration
- 🚫 **Conflict Resolution**: Skip existing templates or handle duplicates
- 🎯 **Dry Run Mode**: Preview migration without making changes
- 📊 **Progress Tracking**: Real-time progress with detailed reporting
- 🔒 **Secure Configuration**: Environment variables and .env file support
- 🚦 **Rate Limiting**: Built-in API rate limiting to prevent throttling
- 📝 **Detailed Logging**: Rich console output with logging levels

## Prerequisites

- Python 3.12 or higher
- Valid WhatsApp Business API access tokens for both source and destination accounts
- WhatsApp Business Account IDs for both accounts
- Required permissions to read from source and write to destination accounts

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

Install uv if you haven't already:
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### Setup

1. Clone or download this repository:
```bash
git clone <repository-url>
cd meta-template-migrator
```

2. Install dependencies using uv:
```bash
# Install dependencies
uv sync

# Or install in development mode with dev dependencies
uv sync --dev
```

### Alternative Installation Methods

If you prefer using pip:
```bash
pip install -e .
```

Or install directly from the repository:
```bash
pip install git+https://github.com/your-username/whatsapp-template-migrator.git
```

## Configuration

### Method 1: Environment Variables

Set the following environment variables:

```bash
export SOURCE_WABA_ID="your_source_waba_id"
export SOURCE_ACCESS_TOKEN="your_source_access_token"
export DESTINATION_WABA_ID="your_destination_waba_id"
export DESTINATION_ACCESS_TOKEN="your_destination_access_token"
```

### Method 2: .env File (Recommended)

1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit the `.env` file with your actual values:
```env
# Source Account (where templates will be copied FROM)
SOURCE_WABA_ID=123456789012345
SOURCE_ACCESS_TOKEN=your_source_access_token_here

# Destination Account (where templates will be copied TO)
DESTINATION_WABA_ID=987654321098765
DESTINATION_ACCESS_TOKEN=your_destination_access_token_here

# Optional: API Version (defaults to v18.0)
API_VERSION=v18.0

# Optional: Rate limiting (requests per minute)
RATE_LIMIT=60

# Optional: Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Optional: Filter templates by status (APPROVED, PENDING, REJECTED, DISABLED, PAUSED)
# Default: APPROVED (only active/approved templates)
FILTER_STATUS=APPROVED
```

## Usage

### Basic Migration

Run the migration script:
```bash
# Using uv (recommended)
uv run python whatsapp_template_migrator.py

# Or if installed with pip
whatsapp-template-migrator
```

### Dry Run (Preview)

See what would be migrated without making changes:
```bash
uv run python whatsapp_template_migrator.py --dry-run
```

### Force Migration (Skip Existing Templates)

Attempt to create all templates, including duplicates:
```bash
uv run python whatsapp_template_migrator.py --no-skip
```

### Custom Configuration File

Use a specific configuration file:
```bash
uv run python whatsapp_template_migrator.py --config-file /path/to/custom.env
```

### Filter by Template Status

Only migrate templates with specific status:
```bash
# Only migrate APPROVED templates (default)
uv run python whatsapp_template_migrator.py --filter-status APPROVED

# Migrate all PENDING templates
uv run python whatsapp_template_migrator.py --filter-status PENDING

# Migrate templates with any status (no filtering)
uv run python whatsapp_template_migrator.py --filter-status ALL
```

### Command Line Options

- `--dry-run`: Show what would be migrated without actually creating templates
- `--no-skip`: Do not skip existing templates (will attempt to create duplicates)
- `--config-file PATH`: Path to custom .env configuration file
- `--filter-status STATUS`: Only migrate templates with specific status (APPROVED, PENDING, REJECTED, DISABLED, PAUSED)

## Template Validation

The script validates templates before migration:

- **Required Fields**: name, category, language, components
- **Name Format**: Alphanumeric characters, underscores, and hyphens only
- **Name Length**: Maximum 512 characters
- **Category**: Must be AUTHENTICATION, MARKETING, or UTILITY
- **Language**: Must be 2-character ISO 639-1 code (e.g., `en`, `es`) or 5-character region-specific code (e.g., `pt_BR`, `en_US`)

## Migration Process

1. **Fetch Source Templates**: Retrieve all templates from the source WABA
2. **Check Existing Templates**: Get existing templates from destination WABA (if skip mode enabled)
3. **Validate Templates**: Check each template for compliance
4. **Create Templates**: Upload valid templates to destination WABA
5. **Report Results**: Display detailed migration summary

## Output

The script provides:

- **Progress Indicators**: Real-time progress with spinners
- **Results Table**: Detailed table showing each template's status
- **Migration Summary**: Total counts of created, skipped, and failed templates
- **Error Details**: Specific error messages for failed templates

### Example Output

```
Starting WhatsApp Template Migration

┌─────────────────────┬──────────┬─────────────────────────────┐
│ Template Name       │ Status   │ Details                     │
├─────────────────────┼──────────┼─────────────────────────────┤
│ welcome_message     │ CREATED  │ Successfully migrated       │
│ order_confirmation  │ SKIPPED  │ Template already exists     │
│ invalid_template    │ INVALID  │ Missing required field: name│
└─────────────────────┴──────────┴─────────────────────────────┘

Migration Summary:
Total templates: 3
Created: 1
Skipped: 1
Failed: 1
```

## Error Handling

The script handles various error scenarios:

- **API Rate Limiting**: Built-in rate limiting with configurable limits
- **Network Errors**: Automatic retry with exponential backoff
- **Invalid Templates**: Detailed validation error messages
- **Authentication Errors**: Clear error messages for token issues
- **Permission Errors**: Specific messages for insufficient permissions

## Security Considerations

- **Access Tokens**: Store tokens securely in environment variables or .env files
- **File Permissions**: Ensure .env files have appropriate permissions (600)
- **Token Rotation**: Regularly rotate access tokens
- **Audit Logging**: Monitor API usage and template changes

## Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Ensure all required variables are set
   - Check .env file syntax and location

2. **"Authentication failed"**
   - Verify access tokens are valid and not expired
   - Check token permissions for both accounts

3. **"Template creation failed"**
   - Check template validation errors
   - Ensure destination account has sufficient permissions
   - Verify template name doesn't conflict with existing templates

4. **"Rate limit exceeded"**
   - Reduce RATE_LIMIT in configuration
   - Wait before retrying

### Debug Mode

Enable debug logging for detailed information:
```bash
export LOG_LEVEL=DEBUG
uv run python whatsapp_template_migrator.py
```

## API Reference

### WhatsApp Business API Endpoints Used

- `GET /{waba-id}/message_templates` - Fetch templates
- `POST /{waba-id}/message_templates` - Create template

### Rate Limits

- Default: 60 requests per minute
- Configurable via `RATE_LIMIT` environment variable
- Automatic rate limiting with sleep intervals

## Development

### Setting up Development Environment

1. Clone the repository:
```bash
git clone <repository-url>
cd meta-template-migrator
```

2. Install development dependencies:
```bash
uv sync --dev
```

3. Run tests:
```bash
uv run pytest
```

4. Format code:
```bash
uv run black .
uv run isort .
```

5. Type checking:
```bash
uv run mypy whatsapp_template_migrator.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the development tools to ensure code quality
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review WhatsApp Business API documentation
3. Open an issue in the repository

## Changelog

### Version 1.0.0
- Initial release
- Basic template migration functionality
- Environment variable configuration
- Dry run mode
- Comprehensive validation
- Rich console output
- Rate limiting support
