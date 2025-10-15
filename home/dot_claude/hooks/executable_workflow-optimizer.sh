#!/bin/bash
# Automatic workflow optimization for Claude Code

echo "SYSTEM CONTEXT - Process every request with these guidelines:
- Be thorough in your analysis and implementation
- Take your time, I'm in no rush
- Think step-by-step for complex tasks
- Use context7 for documentation lookups
- Look for edge cases and potential issues
- Challenge assumptions and provide substantive technical analysis"

# Check if we're in a Rails project
if [ -f "Gemfile" ] && grep -q "rails" Gemfile 2>/dev/null; then
    echo ""
    echo "RAILS PROJECT DETECTED:
- Use context7 for Rails/Ruby documentation
- Reference Rails 8 conventions and best practices
- Consider security implications (CSRF, SQL injection, XSS, etc.)"
fi
