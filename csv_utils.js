/**
 * csv_utils.js - Standard RFC 4180 compliant CSV Parser, Serializer, and Pipeline Processor
 * Zero dependencies, pure Vanilla JavaScript.
 * Compatible with Node.js and modern Web Browsers.
 */

(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        const exports = factory();
        root.parseCSV = exports.parseCSV;
        root.serializeCSV = exports.serializeCSV;
        root.cleanText = exports.cleanText;
        root.isValidSentence = exports.isValidSentence;
        root.detectCSVColumns = exports.detectCSVColumns;
        root.processCSV = exports.processCSV;
        root.createInitialState = exports.createInitialState;
        root.resetCsvState = exports.resetCsvState;
        root.clearOutputState = exports.clearOutputState;
        root.syncCsvIdSelection = exports.syncCsvIdSelection;
        root.updateConfigOption = exports.updateConfigOption;
    }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    const ARABIC_DIGITS = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];

    /**
     * Parses CSV text into an array of rows (arrays of string fields).
     * Strictly conforms to RFC 4180.
     * 
     * @param {string} text - Raw CSV string.
     * @param {Object} [options] - Parser options.
     * @param {boolean} [options.skipEmptyLines=true] - Whether to ignore completely empty lines.
     * @returns {string[][]} Array of records.
     * @throws {Error} When CSV is malformed (e.g., unclosed quote, invalid quote position).
     */
    function parseCSV(text, options = {}) {
        const skipEmptyLines = options.skipEmptyLines !== false;

        if (typeof text !== 'string' || text.length === 0) {
            return [];
        }

        // Strip UTF-8 BOM if present
        if (text.charCodeAt(0) === 0xFEFF) {
            text = text.slice(1);
        }

        if (text.length === 0) {
            return [];
        }

        const rows = [];
        let currentRow = [];
        let currentField = '';
        let isQuotedField = false;
        let fieldClosed = false;
        let fieldStarted = false;
        let quoteStartLine = 1;
        let currentLine = 1;
        let i = 0;
        const len = text.length;

        function finishField() {
            currentRow.push(currentField);
            currentField = '';
            isQuotedField = false;
            fieldClosed = false;
            fieldStarted = false;
        }

        function finishRow() {
            finishField();
            const isEmptyRow = currentRow.length === 1 && currentRow[0] === '';
            if (!isEmptyRow || !skipEmptyLines) {
                rows.push(currentRow);
            }
            currentRow = [];
        }

        while (i < len) {
            const char = text[i];

            if (fieldClosed) {
                // Strictly RFC 4180: after closing quote, only delimiter or newline/EOF allowed
                if (char === ',') {
                    finishField();
                    i++;
                    continue;
                } else if (char === '\r' || char === '\n') {
                    if (char === '\r' && i + 1 < len && text[i + 1] === '\n') {
                        i++;
                    }
                    finishRow();
                    currentLine++;
                    i++;
                    continue;
                } else {
                    throw new Error(`خطای ساختار CSV: کاراکتر غیرمجاز پس از بسته‌شدن کوتیشن در سطر/رکورد تقریبی ${currentLine}`);
                }
            }

            if (isQuotedField) {
                if (char === '"') {
                    // Escaped double quote ("")
                    if (i + 1 < len && text[i + 1] === '"') {
                        currentField += '"';
                        i += 2;
                        continue;
                    } else {
                        // Closing quote for this field
                        isQuotedField = false;
                        fieldClosed = true;
                        i++;
                        continue;
                    }
                } else {
                    currentField += char;
                    if (char === '\n') {
                        currentLine++;
                    }
                    i++;
                    continue;
                }
            } else {
                // Field start or unquoted field
                if (!fieldStarted) {
                    fieldStarted = true;
                    if (char === '"') {
                        isQuotedField = true;
                        quoteStartLine = currentLine;
                        i++;
                        continue;
                    }
                }

                // In unquoted field: quote is NOT allowed in middle
                if (char === '"') {
                    throw new Error(`خطای ساختار CSV: کوتیشن فقط در ابتدای فیلد مجاز است در سطر/رکورد تقریبی ${currentLine}`);
                } else if (char === ',') {
                    finishField();
                    i++;
                    continue;
                } else if (char === '\r' || char === '\n') {
                    if (char === '\r' && i + 1 < len && text[i + 1] === '\n') {
                        i++;
                    }
                    finishRow();
                    currentLine++;
                    i++;
                    continue;
                } else {
                    currentField += char;
                    i++;
                    continue;
                }
            }
        }

        // Strict error on unclosed quote
        if (isQuotedField) {
            throw new Error(`خطای ساختار CSV: نقل‌قول (کوتیشن) بسته نشده در سطر/رکورد تقریبی ${quoteStartLine}`);
        }

        if (fieldStarted || currentField.length > 0 || currentRow.length > 0 || fieldClosed) {
            finishRow();
        }

        return rows;
    }

    /**
     * Serializes an array of rows into RFC 4180 compliant CSV string.
     * Always prepends UTF-8 BOM (\uFEFF) for Persian Excel compatibility.
     * 
     * @param {Array<Array<*>>} rows - 2D array of rows and column fields.
     * @returns {string} RFC 4180 CSV string with UTF-8 BOM.
     */
    function serializeCSV(rows) {
        if (!Array.isArray(rows) || rows.length === 0) {
            return '\uFEFF';
        }

        const lines = rows.map(row => {
            if (!Array.isArray(row)) return '';
            return row.map(val => {
                const str = (val === null || val === undefined) ? '' : String(val);
                // Quote if field contains quote, comma, carriage return or newline
                if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
                    return '"' + str.replace(/"/g, '""') + '"';
                }
                return str;
            }).join(',');
        });

        return '\uFEFF' + lines.join('\r\n');
    }

    /**
     * Core text cleaning and normalization function.
     * Used identically in browser UI and test pipeline.
     */
    function cleanText(text, options = {}) {
        let res = text || '';

        if (options.removeHtml !== false) {
            res = res.replace(/<[^>]*>/g, ' ');
        }
        if (options.removeUrls !== false) {
            res = res.replace(/https?:\/\/\S+|www\.\S+/gi, '');
        }
        if (options.removeEmails !== false) {
            res = res.replace(/[\w\.-]+@[\w\.-]+\.\w+/gi, '');
        }
        if (options.removeMentions !== false) {
            res = res.replace(/@[\w\d_]+/g, '');
        }
        if (options.removeEmojis !== false) {
            res = res.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '');
        }
        if (options.cleanHashtags !== false) {
            res = res.replace(/#([\w\u0600-\u06FF]+)/g, (m, p1) => p1.replace(/_/g, ' '));
        }
        if (options.normalizeChars !== false) {
            res = res
                .replace(/ي/g, 'ی')
                .replace(/ك/g, 'ک')
                .replace(/ة/g, 'ه')
                .replace(/ؤ/g, 'و')
                .replace(/إ/g, 'ا')
                .replace(/أ/g, 'ا')
                .replace(/ء/g, '')
                .replace(/\u0640/g, '');
        }
        if (options.removeDiacritics !== false) {
            res = res.replace(/[\u064B-\u0652\u0670]/g, '');
        }
        if (options.semiSpace !== false) {
            const zwnj = '\u200c';
            res = res.replace(/\b(می|نمی)\s+/g, `$1${zwnj}`);
            res = res.replace(/\s+(ها|های|تر|ترین|ام|ات|اش|ایم|اید|اند)\b/g, `${zwnj}$1`);
            res = res.replace(/\u200c{2,}/g, zwnj);
        }
        if (options.persianDigits !== false) {
            for (let i = 0; i < 10; i++) {
                res = res.replace(new RegExp(i.toString(), 'g'), PERSIAN_DIGITS[i]);
                res = res.replace(new RegExp(ARABIC_DIGITS[i], 'g'), PERSIAN_DIGITS[i]);
            }
        }
        if (options.cleanPunctuation !== false) {
            res = res.replace(/([!؟?.,،؛:]){2,}/g, '$1');
            res = res.replace(/\s+([!؟?.,،؛:])/g, '$1');
            res = res.replace(/([!؟?.,،؛:])([^\s\d!؟?.,،؛:])/g, '$1 $2');
            res = res.replace(/[ \t]+/g, ' ');
        }

        return res.trim();
    }

    /**
     * Sentence structure validation.
     */
    function isValidSentence(text, minWords = 3, minPersianRatio = 0.5) {
        if (!text || typeof text !== 'string') return false;
        const words = text.trim().split(/\s+/).filter(w => w.length > 0);
        if (words.length < minWords) return false;

        const persianChars = (text.match(/[\u0600-\u06FF]/g) || []).length;
        const totalChars = text.replace(/\s/g, '').length;
        if (totalChars === 0) return false;

        return (persianChars / totalChars) >= minPersianRatio;
    }

    /**
     * Deterministic CSV column and header detection without guessing.
     * @param {string[][]} rows - Parsed CSV rows.
     * @returns {Object} Detection results.
     */
    function detectCSVColumns(rows) {
        if (!rows || rows.length === 0) {
            return { hasHeader: false, textColumnIndex: -1, idColumnIndex: -1, headers: [] };
        }

        const headerRow = rows[0] || [];
        const canonicalTextNames = ['text', 'content', 'متن'];
        const canonicalIdNames = ['id', 'شناسه'];
        const knownHeaderNames = ['id', 'شناسه', 'text', 'content', 'متن', 'cleaned_text'];

        let hasHeader = false;
        let matchedTextIndices = [];
        let matchedIdIndices = [];

        headerRow.forEach((col, idx) => {
            const cleanCol = String(col).trim().toLowerCase();
            if (knownHeaderNames.includes(cleanCol)) {
                hasHeader = true;
            }
            if (canonicalTextNames.includes(cleanCol)) {
                matchedTextIndices.push(idx);
            }
            if (canonicalIdNames.includes(cleanCol)) {
                matchedIdIndices.push(idx);
            }
        });

        return {
            hasHeader: hasHeader,
            // Only select if exactly ONE unique match exists; else -1 (requires user selection)
            textColumnIndex: matchedTextIndices.length === 1 ? matchedTextIndices[0] : -1,
            idColumnIndex: matchedIdIndices.length === 1 ? matchedIdIndices[0] : -1,
            headers: headerRow
        };
    }

    /**
     * Unified CSV pipeline processor shared across UI and test suite.
     * Guarantees multiline cell record boundaries, preserves record IDs,
     * and produces standard ["id", "cleaned_text"] final CSV output.
     * 
     * @param {string} csvText - Raw CSV input text.
     * @param {Object} config - Processing configuration.
     * @returns {Object} Output with rows, finalCsv string, and statistics.
     */
    function processCSV(csvText, config = {}) {
        const parsedRows = parseCSV(csvText, { skipEmptyLines: true });
        if (parsedRows.length === 0) {
            return {
                rows: [],
                finalCsv: '\uFEFF"id","cleaned_text"\r\n',
                stats: { totalRecords: 0, validRecords: 0, removedRecords: 0, duplicatesRemoved: 0 }
            };
        }

        const hasHeader = config.hasHeader !== undefined ? Boolean(config.hasHeader) : true;
        const textColIdx = typeof config.textColumn === 'number' ? config.textColumn : -1;

        if (textColIdx < 0) {
            throw new Error('خطا: ستون متن برای پالایش مشخص نشده است. لطفاً ستون متن را انتخاب کنید.');
        }

        const idColIdx = (config.idColumn !== undefined && config.idColumn !== 'auto' && config.idColumn !== null)
            ? Number(config.idColumn)
            : -1; // -1 means auto-numbering

        const preserveCellNewlines = config.preserveCellNewlines !== false; // default true
        const filterShort = config.filterShort !== false;
        const validateSentence = config.validateSentence !== false;
        const deduplicate = config.deduplicate !== false;
        const cleanOpts = config.cleanOptions || {};

        const dataRows = hasHeader ? parsedRows.slice(1) : parsedRows;
        const cleanedRecords = [];
        const seenTexts = new Set();
        let duplicatesCount = 0;
        let removedCount = 0;
        let autoIdCounter = 1;

        for (let i = 0; i < dataRows.length; i++) {
            const row = dataRows[i];
            if (!row || row.length === 0) continue;

            const rawCell = row[textColIdx] !== undefined ? String(row[textColIdx]) : '';

            // Clean cell content while strictly preserving record boundary
            let cleanedCell = '';
            if (preserveCellNewlines && rawCell.includes('\n')) {
                // Clean each line within cell individually and rejoin with newline
                cleanedCell = rawCell
                    .split(/\r?\n/)
                    .map(subLine => cleanText(subLine, cleanOpts))
                    .filter(subLine => subLine.length > 0)
                    .join('\n');
            } else {
                cleanedCell = cleanText(rawCell, cleanOpts);
            }

            cleanedCell = cleanedCell.trim();

            // Validation checks
            if (cleanedCell.length === 0) {
                removedCount++;
                continue;
            }

            if (filterShort && cleanedCell.split(/\s+/).length < 3) {
                removedCount++;
                continue;
            }

            if (validateSentence && !isValidSentence(cleanedCell)) {
                removedCount++;
                continue;
            }

            if (deduplicate) {
                if (seenTexts.has(cleanedCell)) {
                    duplicatesCount++;
                    removedCount++;
                    continue;
                }
                seenTexts.add(cleanedCell);
            }

            // Determine ID: explicit column value or auto-numbering
            let recordId = '';
            if (idColIdx >= 0 && idColIdx < row.length && String(row[idColIdx]).trim() !== '') {
                recordId = String(row[idColIdx]).trim();
            } else {
                recordId = String(autoIdCounter);
            }
            autoIdCounter++;

            cleanedRecords.push([recordId, cleanedCell]);
        }

        const finalTable = [['id', 'cleaned_text'], ...cleanedRecords];
        const finalCsvString = serializeCSV(finalTable);

        return {
            rows: cleanedRecords,
            finalCsv: finalCsvString,
            stats: {
                totalRecords: dataRows.length,
                validRecords: cleanedRecords.length,
                removedRecords: removedCount,
                duplicatesRemoved: duplicatesCount
            }
        };
    }

    /**
     * Helper functions for state management and transitions
     */
    function createInitialState() {
        return {
            isCsvMode: false,
            csvRawText: '',
            cleanedRecords: [],
            cleanedLines: [],
            cleanedText: '',
            stats: {
                cleanChars: 0,
                cleanWords: 0,
                cleanLines: 0,
                duplicatesRemoved: 0,
                uniqueWords: 0,
                avgSentenceLength: 0,
                avgWordLength: 0,
                hashtags: {},
                wordFrequencies: {},
                charFrequencies: {}
            },
            options: {
                hasHeader: true,
                textColumn: -1,
                idColumn: 'auto'
            }
        };
    }

    function resetCsvState(stateObj) {
        if (!stateObj) return;
        stateObj.isCsvMode = false;
        stateObj.csvRawText = '';
        stateObj.cleanedRecords = [];
        return stateObj;
    }

    function clearOutputState(stateObj) {
        if (!stateObj) return;
        stateObj.cleanedLines = [];
        stateObj.cleanedText = '';
        stateObj.cleanedRecords = [];
        if (!stateObj.stats) {
            stateObj.stats = {};
        }
        stateObj.stats.cleanChars = 0;
        stateObj.stats.cleanWords = 0;
        stateObj.stats.cleanLines = 0;
        stateObj.stats.duplicatesRemoved = 0;
        stateObj.stats.uniqueWords = 0;
        stateObj.stats.avgSentenceLength = 0;
        stateObj.stats.avgWordLength = 0;
        stateObj.stats.hashtags = {};
        stateObj.stats.wordFrequencies = {};
        stateObj.stats.charFrequencies = {};
        return stateObj;
    }

    /**
     * Strictly preserves user ID column selection across input edits.
     * Never auto-switches to an ID column if user explicitly selected 'auto' or a valid column.
     * 
     * @param {string} previousIdSelection - Current selection ("auto" or column index as string).
     * @param {number} newColumnCount - Total available columns in updated input.
     * @returns {string} Preserved selection ("auto" or existing column index).
     */
    function syncCsvIdSelection(previousIdSelection, newColumnCount) {
        if (previousIdSelection === 'auto' || !previousIdSelection) {
            return 'auto';
        }
        const idx = Number(previousIdSelection);
        if (!isNaN(idx) && idx >= 0 && idx < newColumnCount) {
            return String(idx);
        }
        return 'auto';
    }

    /**
     * Updates a configuration option and immediately clears previous output state
     * to prevent downloading stale results.
     * 
     * @param {Object} stateObj - Application state object.
     * @param {string} optionKey - Config key being modified.
     * @param {*} newValue - New config value.
     * @returns {Object} Updated state with output cleared.
     */
    function updateConfigOption(stateObj, optionKey, newValue) {
        if (!stateObj) return;
        if (!stateObj.options) stateObj.options = {};
        stateObj.options[optionKey] = newValue;
        clearOutputState(stateObj);
        return stateObj;
    }

    return {
        parseCSV,
        serializeCSV,
        cleanText,
        isValidSentence,
        detectCSVColumns,
        processCSV,
        createInitialState,
        resetCsvState,
        clearOutputState,
        syncCsvIdSelection,
        updateConfigOption
    };
});
