#!/usr/bin/env python3
"""
WhatsApp Template Migrator

A Python script to migrate WhatsApp Business API templates from one account to another.
Supports environment variables and .env file configuration.
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize rich console
console = Console()


@dataclass
class TemplateConfig:
    """Configuration for WhatsApp template migration."""

    source_waba_id: str
    destination_waba_id: str
    source_access_token: str
    destination_access_token: str
    api_version: str = "v18.0"
    rate_limit: int = 60
    log_level: str = "INFO"
    filter_status: str = "APPROVED"


class WhatsAppTemplateMigrator:
    """Main class for migrating WhatsApp templates between accounts."""

    def __init__(self, config: TemplateConfig):
        self.config = config
        self.base_url = f"https://graph.facebook.com/{config.api_version}"
        self.setup_logging()

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60 / config.rate_limit

    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True)],
        )
        self.logger = logging.getLogger("whatsapp_migrator")

    def _rate_limit(self):
        """Implement rate limiting for API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(
        self, method: str, url: str, headers: Dict, **kwargs
    ) -> requests.Response:
        """Make HTTP request with rate limiting and error handling."""
        self._rate_limit()

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise

    def get_templates(self, waba_id: str, access_token: str) -> List[Dict]:
        """Fetch all templates from a WhatsApp Business Account."""
        url = f"{self.base_url}/{waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        self.logger.info(f"Fetching templates from WABA: {waba_id}")

        try:
            response = self._make_request("GET", url, headers)
            data = response.json()

            all_templates = data.get("data", [])

            # Filter templates by status (skip filtering if ALL is specified)
            if self.config.filter_status == "ALL":
                filtered_templates = all_templates
                self.logger.info(
                    f"Found {len(all_templates)} total templates (no status filtering)"
                )
            else:
                filtered_templates = [
                    template
                    for template in all_templates
                    if template.get("status") == self.config.filter_status
                ]
                self.logger.info(
                    f"Found {len(all_templates)} total templates, {len(filtered_templates)} templates with status '{self.config.filter_status}'"
                )

            return filtered_templates

        except Exception as e:
            self.logger.error(f"Failed to fetch templates: {e}")
            return []

    def get_existing_templates(
        self, waba_id: str, access_token: str
    ) -> Dict[str, Dict]:
        """Get existing templates as a dictionary keyed by template name."""
        templates = self.get_templates(waba_id, access_token)
        return {template["name"]: template for template in templates}

    def validate_template(self, template: Dict) -> Tuple[bool, List[str]]:
        """Validate template structure and content."""
        errors = []

        # Required fields
        required_fields = ["name", "category", "language", "components"]
        for field in required_fields:
            if field not in template:
                errors.append(f"Missing required field: {field}")

        # Validate name format
        if "name" in template:
            name = template["name"]
            if not name.replace("_", "").replace("-", "").isalnum():
                errors.append(
                    "Template name must contain only alphanumeric characters, underscores, and hyphens"
                )
            if len(name) > 512:
                errors.append("Template name must be 512 characters or less")

        # Validate category
        valid_categories = ["AUTHENTICATION", "MARKETING", "UTILITY"]
        if "category" in template and template["category"] not in valid_categories:
            errors.append(
                f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

        # Validate language
        if "language" in template:
            language = template["language"]
            # Accept both ISO 639-1 (2 chars) and region-specific (5 chars like pt_BR, en_US)
            if len(language) not in [2, 5]:
                errors.append(
                    "Language code must be 2 characters (ISO 639-1) or 5 characters (region-specific like pt_BR)"
                )
            elif len(language) == 5 and not language.count("_") == 1:
                errors.append(
                    "Region-specific language code must be in format 'xx_XX' (e.g., pt_BR)"
                )

        return len(errors) == 0, errors

    def create_template(self, waba_id: str, access_token: str, template: Dict) -> bool:
        """Create a template in the destination WABA."""
        url = f"{self.base_url}/{waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Prepare template data for creation
        template_data = {
            "name": template["name"],
            "category": template["category"],
            "language": template["language"],
            "components": template["components"],
        }

        # Add optional fields if present
        optional_fields = ["status", "quality_score"]
        for field in optional_fields:
            if field in template:
                template_data[field] = template[field]

        self.logger.info(f"Creating template: {template['name']}")

        try:
            response = self._make_request("POST", url, headers, json=template_data)
            result = response.json()

            if "id" in result:
                self.logger.info(
                    f"Successfully created template: {template['name']} (ID: {result['id']})"
                )
                return True
            else:
                self.logger.error(
                    f"Failed to create template {template['name']}: {result}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Failed to create template {template['name']}: {e}")
            return False

    def migrate_templates(
        self, dry_run: bool = False, skip_existing: bool = True
    ) -> Dict[str, int]:
        """Migrate templates from source to destination account."""
        console.print("\n[bold blue]Starting WhatsApp Template Migration[/bold blue]")

        # Get source templates
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching source templates...", total=None)
            source_templates = self.get_templates(
                self.config.source_waba_id, self.config.source_access_token
            )
            progress.update(task, description="Source templates fetched")

        if not source_templates:
            console.print("[red]No templates found in source account[/red]")
            return {"total": 0, "created": 0, "skipped": 0, "failed": 0}

        # Get destination templates for conflict checking
        existing_templates = {}
        if skip_existing:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Checking existing templates...", total=None)
                existing_templates = self.get_existing_templates(
                    self.config.destination_waba_id,
                    self.config.destination_access_token,
                )
                progress.update(task, description="Existing templates checked")

        # Migration statistics
        stats = {
            "total": len(source_templates),
            "created": 0,
            "skipped": 0,
            "failed": 0,
        }

        # Create results table
        table = Table(title="Migration Results")
        table.add_column("Template Name", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="white")

        # Process each template
        for template in source_templates:
            template_name = template["name"]

            # Validate template
            is_valid, errors = self.validate_template(template)
            if not is_valid:
                table.add_row(template_name, "[red]INVALID[/red]", "; ".join(errors))
                stats["failed"] += 1
                continue

            # Check if template already exists
            if skip_existing and template_name in existing_templates:
                table.add_row(
                    template_name, "[yellow]SKIPPED[/yellow]", "Template already exists"
                )
                stats["skipped"] += 1
                continue

            if dry_run:
                table.add_row(template_name, "[blue]DRY RUN[/blue]", "Would be created")
                stats["created"] += 1
            else:
                # Create template
                success = self.create_template(
                    self.config.destination_waba_id,
                    self.config.destination_access_token,
                    template,
                )

                if success:
                    table.add_row(
                        template_name, "[green]CREATED[/green]", "Successfully migrated"
                    )
                    stats["created"] += 1
                else:
                    table.add_row(template_name, "[red]FAILED[/red]", "Creation failed")
                    stats["failed"] += 1

        # Display results
        console.print(table)

        # Display summary
        console.print(f"\n[bold]Migration Summary:[/bold]")
        console.print(f"Total templates: {stats['total']}")
        console.print(f"Created: {stats['created']}")
        console.print(f"Skipped: {stats['skipped']}")
        console.print(f"Failed: {stats['failed']}")

        return stats


def load_config() -> TemplateConfig:
    """Load configuration from environment variables and .env file."""
    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Get required configuration
    source_waba_id = os.getenv("SOURCE_WABA_ID")
    destination_waba_id = os.getenv("DESTINATION_WABA_ID")
    source_access_token = os.getenv("SOURCE_ACCESS_TOKEN")
    destination_access_token = os.getenv("DESTINATION_ACCESS_TOKEN")

    # Validate required fields
    missing_fields = []
    if not source_waba_id:
        missing_fields.append("SOURCE_WABA_ID")
    if not destination_waba_id:
        missing_fields.append("DESTINATION_WABA_ID")
    if not source_access_token:
        missing_fields.append("SOURCE_ACCESS_TOKEN")
    if not destination_access_token:
        missing_fields.append("DESTINATION_ACCESS_TOKEN")

    if missing_fields:
        console.print(
            f"[red]Error: Missing required environment variables: {', '.join(missing_fields)}[/red]"
        )
        console.print(
            "[yellow]Please set these variables or create a .env file based on env.example[/yellow]"
        )
        sys.exit(1)

    return TemplateConfig(
        source_waba_id=source_waba_id,
        destination_waba_id=destination_waba_id,
        source_access_token=source_access_token,
        destination_access_token=destination_access_token,
        api_version=os.getenv("API_VERSION", "v18.0"),
        rate_limit=int(os.getenv("RATE_LIMIT", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        filter_status=os.getenv("FILTER_STATUS", "APPROVED"),
    )


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be migrated without actually creating templates",
)
@click.option(
    "--no-skip",
    is_flag=True,
    help="Do not skip existing templates (will attempt to create duplicates)",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to .env configuration file",
)
@click.option(
    "--filter-status",
    type=click.Choice(["APPROVED", "PENDING", "REJECTED", "DISABLED", "PAUSED", "ALL"]),
    help="Only migrate templates with this status (default: APPROVED, use ALL for no filtering)",
)
def main(
    dry_run: bool,
    no_skip: bool,
    config_file: Optional[str],
    filter_status: Optional[str],
):
    """Migrate WhatsApp templates from one account to another."""

    # Load configuration
    if config_file:
        load_dotenv(config_file)

    try:
        config = load_config()
    except SystemExit:
        return

    # Override filter status if provided via CLI
    if filter_status:
        config.filter_status = filter_status

    # Create migrator instance
    migrator = WhatsAppTemplateMigrator(config)

    # Run migration
    try:
        stats = migrator.migrate_templates(dry_run=dry_run, skip_existing=not no_skip)

        if dry_run:
            console.print(
                "\n[yellow]This was a dry run. No templates were actually created.[/yellow]"
            )
            console.print(
                "[blue]Run without --dry-run to perform the actual migration.[/blue]"
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Migration interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Migration failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
