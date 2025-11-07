#!/usr/bin/env python3
"""
Environment Setup Utility for Flashcard Study App

This script helps set up environment configurations for different deployment scenarios.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def list_available_environments() -> List[str]:
    """List all available environment configurations."""
    project_root = get_project_root()
    env_files = project_root.glob('.env.*')
    environments = []

    for env_file in env_files:
        if env_file.name != '.env.example':
            env_name = env_file.name.replace('.env.', '')
            environments.append(env_name)

    return sorted(environments)


def copy_env_file(environment: str, force: bool = False) -> bool:
    """Copy environment-specific file to .env"""
    project_root = get_project_root()
    source_file = project_root / f'.env.{environment}'
    target_file = project_root / '.env'

    if not source_file.exists():
        print(f"❌ Environment file .env.{environment} does not exist")
        return False

    if target_file.exists() and not force:
        print(f"⚠️  .env file already exists. Use --force to overwrite")
        return False

    try:
        shutil.copy2(source_file, target_file)
        print(f"✅ Copied .env.{environment} to .env")
        return True
    except Exception as e:
        print(f"❌ Failed to copy environment file: {e}")
        return False


def validate_env_file(env_path: Path) -> Dict[str, List[str]]:
    """Validate environment file and return missing/problematic variables."""
    if not env_path.exists():
        return {"missing": ["File does not exist"]}

    required_vars = [
        "DATABASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DEFAULT_AI_PROVIDER",
    ]

    sensitive_vars = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "SESSION_SECRET",
        "DATABASE_URL",
    ]

    issues = {"missing": [], "insecure": [], "warnings": []}

    try:
        with open(env_path, 'r') as f:
            content = f.read()

        # Check for required variables
        for var in required_vars:
            if f"{var}=" not in content:
                issues["missing"].append(f"Missing required variable: {var}")

        # Check for insecure values
        lines = content.split('\n')
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key in sensitive_vars:
                    if value in ['', 'your-key-here', 'test-key', 'change-me']:
                        issues["insecure"].append(f"Insecure value for {key}")
                    elif 'localhost' in value and env_path.name.endswith('production'):
                        issues["warnings"].append(f"Localhost URL in production config: {key}")

    except Exception as e:
        issues["missing"].append(f"Error reading file: {e}")

    return issues


def show_environment_info(environment: str) -> None:
    """Show detailed information about an environment."""
    project_root = get_project_root()
    env_file = project_root / f'.env.{environment}'

    if not env_file.exists():
        print(f"❌ Environment .env.{environment} does not exist")
        return

    print(f"\n📋 Environment: {environment}")
    print(f"📁 File: {env_file}")

    # Validate the environment
    issues = validate_env_file(env_file)

    if issues["missing"]:
        print("\n❌ Missing/Error:")
        for issue in issues["missing"]:
            print(f"  • {issue}")

    if issues["insecure"]:
        print("\n🔒 Security Issues:")
        for issue in issues["insecure"]:
            print(f"  • {issue}")

    if issues["warnings"]:
        print("\n⚠️  Warnings:")
        for issue in issues["warnings"]:
            print(f"  • {issue}")

    if not any(issues.values()):
        print("\n✅ Environment configuration looks good!")


def generate_secure_secret() -> str:
    """Generate a secure session secret."""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(64))


def setup_production_env() -> None:
    """Interactive setup for production environment."""
    project_root = get_project_root()
    prod_env = project_root / '.env.production'

    print("🚀 Setting up production environment...")
    print("\nThis will help you configure secure production settings.")

    # Generate secure session secret
    session_secret = generate_secure_secret()
    print(f"\n🔑 Generated secure session secret (64 characters)")

    # Collect required information
    print("\nPlease provide the following information:")

    database_url = input("Database URL (postgresql://...): ")
    anthropic_key = input("Anthropic API Key (sk-ant-...): ")
    openai_key = input("OpenAI API Key (sk-...): ")
    domain = input("Your domain (e.g., myapp.com): ")

    # Create production config
    config_content = f"""# Production Environment Configuration
# Generated on {import datetime; datetime.datetime.now().isoformat()}

# Database
DATABASE_URL={database_url}

# AI Providers
ANTHROPIC_API_KEY={anthropic_key}
OPENAI_API_KEY={openai_key}
DEFAULT_AI_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o

# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# CORS Settings
CORS_ORIGINS=["https://{domain}", "https://www.{domain}"]

# Session Settings
SESSION_SECRET={session_secret}

# Feature Flags
ENABLE_REGISTRATION=false
ENABLE_DEMO_MODE=false
ENABLE_API_DOCS=false

# Performance Settings
MAX_WORKERS=4
MAX_CONNECTIONS=100

# Security Settings
HTTPS_ONLY=true
SECURE_COOKIES=true
HSTS_MAX_AGE=31536000
"""

    with open(prod_env, 'w') as f:
        f.write(config_content)

    print(f"\n✅ Created {prod_env}")
    print("⚠️  Remember to keep this file secure and never commit it to version control!")


def main():
    """Main CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Environment setup utility")
    parser.add_argument("command", choices=["list", "use", "validate", "info", "setup-prod"],
                       help="Command to run")
    parser.add_argument("environment", nargs="?", help="Environment name")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing .env")

    args = parser.parse_args()

    if args.command == "list":
        print("🌍 Available environments:")
        environments = list_available_environments()
        for env in environments:
            print(f"  • {env}")

        if not environments:
            print("  No environment files found")

    elif args.command == "use":
        if not args.environment:
            print("❌ Please specify an environment name")
            sys.exit(1)

        success = copy_env_file(args.environment, args.force)
        if success:
            print(f"🎯 Active environment: {args.environment}")
            print("💡 Run 'python scripts/setup-env.py validate' to check configuration")

    elif args.command == "validate":
        project_root = get_project_root()
        env_file = project_root / '.env'

        if not env_file.exists():
            print("❌ No .env file found. Run 'use' command first.")
            sys.exit(1)

        issues = validate_env_file(env_file)

        print("🔍 Validating .env file...")

        if issues["missing"]:
            print("\n❌ Issues found:")
            for issue in issues["missing"]:
                print(f"  • {issue}")

        if issues["insecure"]:
            print("\n🔒 Security warnings:")
            for issue in issues["insecure"]:
                print(f"  • {issue}")

        if issues["warnings"]:
            print("\n⚠️  Warnings:")
            for issue in issues["warnings"]:
                print(f"  • {issue}")

        if not any(issues.values()):
            print("\n✅ Environment configuration is valid!")

    elif args.command == "info":
        if not args.environment:
            print("❌ Please specify an environment name")
            sys.exit(1)

        show_environment_info(args.environment)

    elif args.command == "setup-prod":
        setup_production_env()


if __name__ == "__main__":
    main()