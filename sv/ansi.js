// sv/ansi.js

/**
 * A map of ANSI color codes to their corresponding CSS variable names.
 * This ensures consistency with the variables defined in the global CSS.
 */
export const ansiCodeToCssVar = {
    '30': 'var(--ansi-black)', '31': 'var(--ansi-red)', '32': 'var(--ansi-green)', '33': 'var(--ansi-yellow)',
    '34': 'var(--ansi-blue)', '35': 'var(--ansi-magenta)', '36': 'var(--ansi-cyan)', '37': 'var(--ansi-white)',
    '90': 'var(--ansi-bright-black)', '91': 'var(--ansi-bright-red)', '92': 'var(--ansi-bright-green)', '93': 'var(--ansi-bright-yellow)',
    '94': 'var(--ansi-bright-blue)', '95': 'var(--ansi-bright-magenta)', '96': 'var(--ansi-bright-cyan)', '97': 'var(--ansi-bright-white)',
};

/**
 * Parses a string containing ANSI escape codes and converts it into HTML with inline styles.
 * It handles standard and bright colors, as well as the reset code.
 * It also strips some common control characters like bell and clear screen.
 * @param {string} text The text to parse.
 * @returns {string} The HTML representation of the text.
 */
export function parseAnsi(text) {
    if (typeof text !== 'string') return '';
    // This regex handles standard color codes and also the reset code which can be `[0m` or just `[m`.
    const ansiRegex = /\u001b\[(\d*)m/g;
    let openSpan = false;

    // Strip some common non-rendering control characters like bell and clear screen.
    const controlCharsRegex = /\u0007|\x1b\[H\x1b\[2J|\x1b\[2J/g;
    text = text.replace(controlCharsRegex, '');

    // Sanitize the text to prevent HTML injection.
    let sanitizedText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

    let html = sanitizedText.replace(ansiRegex, (match, code) => {
        let newHtml = '';
        if (openSpan) {
            newHtml += '</span>';
            openSpan = false;
        }
        // An empty code or a '0' are both reset codes.
        if (code === '0' || code === '') {
            // This is a reset code, we just closed the span.
        } else if (ansiCodeToCssVar[code]) {
            newHtml += `<span style="color: ${ansiCodeToCssVar[code]}">`;
            openSpan = true;
        }
        return newHtml;
    });

    // Ensure any open span is closed at the end of the string.
    if (openSpan) {
        html += '</span>';
    }
    return html;
}

/**
 * Strips all ANSI escape codes from a string.
 * @param {string} text The text to strip codes from.
 * @returns {string} The text without any ANSI codes or control characters.
 */
export function stripAnsi(text) {
    if (typeof text !== 'string') return '';
    const ansiRegex = /\u001b\[\d*m/g; // Use * to match empty codes as well
    const controlCharsRegex = /\u0007|\x1b\[H\x1b\[2J|\x1b\[2J/g;
    return text.replace(ansiRegex, '').replace(controlCharsRegex, '');
}