# Global OpenCode Agent Instructions

Managed by chezmoi - https://github.com/btuckerc/boilerplate

These instructions apply to all OpenCode sessions globally. Project-specific instructions should be placed in the project's AGENTS.md file.

## Core Workflow Principles

Process every request with these guidelines:

- **Be thorough in your analysis and implementation**
  - Don't rush to solutions
  - Explore edge cases and potential issues
  - Consider long-term maintainability

- **Take your time, I'm in no rush**
  - Quality over speed
  - Think through the implications of changes
  - Test your assumptions

- **Think step-by-step for complex tasks**
  - Break down large problems into manageable pieces
  - Explain your reasoning as you work
  - Document important decisions

- **Use documentation lookups when needed**
  - Reference official documentation for accuracy
  - Verify API usage and best practices
  - Stay current with framework conventions

- **Look for edge cases and potential issues**
  - Consider error handling
  - Think about boundary conditions
  - Anticipate failure modes

- **Challenge assumptions and provide substantive technical analysis**
  - Question requirements when they seem unclear or problematic
  - Provide alternative approaches when appropriate
  - Explain trade-offs between different solutions

## Security Considerations

Always consider security implications:

- **Input Validation**: Validate and sanitize all user inputs
- **Authentication & Authorization**: Respect access controls
- **Data Protection**: Handle sensitive data appropriately
- **Common Vulnerabilities**: Watch for CSRF, SQL injection, XSS, etc.
- **Dependency Security**: Be aware of known vulnerabilities in dependencies

## Code Quality Standards

- **Consistency**: Follow existing code style and patterns in the project
- **Readability**: Write clear, self-documenting code
- **Testing**: Consider test coverage for new functionality
- **Performance**: Be mindful of performance implications
- **Documentation**: Add comments for complex logic

## Framework-Specific Guidance

### Rails Projects (detected by Gemfile with 'rails')

- Reference Rails 8 conventions and best practices
- Use Rails idioms (e.g., ActiveRecord, concerns, helpers)
- Follow RESTful routing patterns
- Consider security implications (CSRF, SQL injection, XSS, mass assignment)
- Use Rails generators when appropriate
- Leverage Rails testing frameworks (RSpec, Minitest)

### Node.js/JavaScript Projects

- Follow modern ES6+ syntax
- Use appropriate package managers (npm, pnpm, yarn, bun)
- Consider async/await patterns
- Handle promises correctly
- Use appropriate error handling

### Python Projects

- Follow PEP 8 style guidelines
- Use virtual environments appropriately
- Consider type hints where beneficial
- Handle exceptions properly
- Use appropriate standard library modules

## File Organization

- Keep related code together
- Follow the project's existing structure
- Create new files/modules when appropriate
- Avoid creating unnecessary files

## Communication

- Explain complex decisions
- Provide context for changes
- Ask clarifying questions when requirements are unclear
- Suggest improvements when you see opportunities
