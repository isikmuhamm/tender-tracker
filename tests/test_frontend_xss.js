const fs = require('fs');
const path = require('path');

const appJsPath = path.join(__dirname, '../static/js/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

const lines = appJsContent.split(/\r?\n/);
const helperCode = lines.slice(4, 22).join('\n');

eval(helperCode);

function assert(condition, message) {
    if (!condition) {
        throw new Error(message || "Assertion failed");
    }
}

try {
    const xssPayload = '<script>alert("XSS")</script>';
    const escaped = escapeHtml(xssPayload);
    assert(escaped === '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;', "escapeHtml should escape script tags");
    
    const attributePayload = 'onload="alert(1)"';
    const escapedAttr = escapeHtml(attributePayload);
    assert(escapedAttr.includes('&quot;'), "escapeHtml should escape double quotes");
    
    const safeHttp = 'http://example.com';
    assert(safeLink(safeHttp) === safeHttp, "safeLink should allow http urls");
    
    const safeHttps = 'https://example.com/path?param=1';
    assert(safeLink(safeHttps) === safeHttps, "safeLink should allow https urls");
    
    const unsafeJavascript = 'javascript:alert(1)';
    assert(safeLink(unsafeJavascript) === '#', "safeLink should block javascript scheme");
    
    const unsafeData = 'data:text/html,<script>alert(1)</script>';
    assert(safeLink(unsafeData) === '#', "safeLink should block data scheme");
    
    console.log("All frontend XSS tests passed successfully!");
} catch (error) {
    console.error("Test failed:", error.message);
    process.exit(1);
}
