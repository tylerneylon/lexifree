# Guidelines for Slider Interface Codebase

## Commands
- Run local server: `python run_site.py` (port 80) or `python run_site.py --debug` (port 8080, verbose output)
- Format code: `npx prettier --write .`
- Lint code: `npx eslint .`

## Code Style Guidelines
- **Line Length**: Max 80 characters per line
- **Comments**: Complete grammatically correct English sentences starting with capitalized word and ending with punctuation
- **Indentation**: 2 spaces for JavaScript
- **Variables**: Use camelCase for variables and functions
- **DOM Manipulation**: Prefer direct array indexing over querySelector when possible for performance
- **Error Handling**: Use appropriate error checking for DOM operations
- **CSS**: Use .className format for class selectors
- **Scroll Handling**: Use requestAnimationFrame for scroll events
- **JS Language**: Use vanilla JavaScript (no frameworks)

## Patterns
- Use event listeners for user interactions
- Keep global state minimal and well-documented
- Optimize DOM operations for performance, especially with large datasets