// Smart Quotes Converter
// Converts straight quotes to typographer's (curly) quotes
// Handles both single and double quotes with context awareness

#target indesign

if (app.documents.length === 0) {
  alert("Please open a document first.");
  exit();
}

var doc = app.activeDocument;
var story = doc.stories[0];

if (!story) {
  alert("No text found in document.");
  exit();
}

// Typographer's quotes
var ldquo = """; // "
var rdquo = """; // "
var lsquo = "'"; // '
var rsquo = "'"; // '

// Convert text
var text = story.contents;
var result = text;

// Replace straight quotes with smart quotes
// This uses a simple but effective approach:
// 1. Replace quotes after spaces, opening brackets, newlines with opening quotes
// 2. Replace quotes before spaces, closing brackets, punctuation with closing quotes
// 3. Handle contractions and possessives with right single quote

// Double quotes - opening (after space, newline, or at start)
result = result.replace(/(\s|^|[\[\(])"/g, "$1" + ldquo);

// Double quotes - closing (before space, punctuation, closing bracket, or end)
result = result.replace(/"(\s|[,\.;:!?\)\]]|\n|$)/g, rdquo + "$1");

// Single quotes - contractions and possessives (between letters)
result = result.replace(/([a-zA-Z])'([a-zA-Z])/g, "$1" + rsquo + "$2");

// Single quotes - opening (after space, newline, or at start)
result = result.replace(/(\s|^|[\[\(])'/g, "$1" + lsquo);

// Single quotes - closing (before space, punctuation, closing bracket, or end)
result = result.replace(/'(\s|[,\.;:!?\)\]]|\n|$)/g, rsquo + "$1");

// Apply the converted text back
story.contents = result;

alert("Smart quotes applied successfully!");
