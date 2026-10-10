/**
 * test_phase1.js - Automated Unit & Functional Tests for Phase 1
 * Uses native Node.js assert module (zero dependencies).
 * 
 * شفاف‌سازی و محدودیت آزمون‌ها:
 * این آزمون‌ها در محیط Node.js اجرا می‌شوند و توابع خالص (parseCSV, serializeCSV, cleanText, processCSV)،
 * تطابق با استاندارد RFC 4180 و منطق مدیریت State را در سطح Unit/Functional ارزیابی می‌کنند.
 * این تست‌ها رویدادهای زنده DOM مرورگر را مستقیماً پوشش نمی‌دهند.
 * 
 * Run with: node test_phase1.js
 */

const assert = require('assert');
const {
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
} = require('./csv_utils.js');

let totalTests = 0;
let passedTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        fn();
        console.log(`  ✔ [PASS] ${name}`);
        passedTests++;
    } catch (err) {
        console.error(`  ✖ [FAIL] ${name}`);
        console.error(`     Error: ${err.message}`);
        throw err;
    }
}

console.log('=====================================================');
console.log('  اجرای آزمون‌های جامع مرحله ۱ (CSV Parsing, Security & Pipeline)');
console.log('=====================================================\n');

// ----------------------------------------------------
// بخش ۱: آزمون‌های واحد پارسر و سازنده استاندارد RFC 4180
// ----------------------------------------------------

// 1. Empty input
runTest('Unit Test: ورودی کاملاً خالی باید آرایه خالی برگرداند', () => {
    assert.deepStrictEqual(parseCSV(''), []);
    assert.deepStrictEqual(parseCSV(null), []);
    assert.deepStrictEqual(parseCSV(undefined), []);
});

// 2. Persian text with BOM
runTest('Unit Test: متن فارسی همراه با کاراکتر پیشوند BOM (\uFEFF) باید بدون کاراکتر اضافه استخراج شود', () => {
    const input = '\uFEFFشناسه,متن_فارسی\n1,این یک متن تستی فارسی است\n2,پروژه پاک‌سازی داده‌ها';
    const result = parseCSV(input);
    assert.strictEqual(result.length, 3);
    assert.deepStrictEqual(result[0], ['شناسه', 'متن_فارسی']);
    assert.deepStrictEqual(result[1], ['1', 'این یک متن تستی فارسی است']);
    assert.deepStrictEqual(result[2], ['2', 'پروژه پاک‌سازی داده‌ها']);
});

// 3. Comma inside quotes
runTest('Unit Test: کامای داخل کوتیشن نباید سلول را تقسیم کند', () => {
    const input = '1,"تهران، میدان آزادی",معتبر\n2,"شیراز, میدان ارم",در حال بررسی';
    const result = parseCSV(input);
    assert.strictEqual(result.length, 2);
    assert.strictEqual(result[0].length, 3);
    assert.strictEqual(result[0][1], 'تهران، میدان آزادی');
    assert.strictEqual(result[1][1], 'شیراز, میدان ارم');
});

// 4. Double quotes escaped
runTest('Unit Test: کوتیشن دوتایی اسکیپ‌شده ("") باید به یک کوتیشن منفرد تبدیل شود', () => {
    const input = '1,"کتاب ""شاهنامه"" فردوسی",ادبیات\n2,"عبارت ""سلام دنیا""",کد';
    const result = parseCSV(input);
    assert.strictEqual(result.length, 2);
    assert.strictEqual(result[0][1], 'کتاب "شاهنامه" فردوسی');
    assert.strictEqual(result[1][1], 'عبارت "سلام دنیا"');
});

// 5. Newline inside cell (Multiline cell)
runTest('Unit Test: خط جدید (Newline) درون سلول محصور در کوتیشن نباید مرز رکورد را بشکند', () => {
    const input = '1,"سطر اول داخل سلول\nسطر دوم داخل سلول\nسطر سوم",پایان';
    const result = parseCSV(input);
    assert.strictEqual(result.length, 1);
    assert.strictEqual(result[0].length, 3);
    assert.strictEqual(result[0][0], '1');
    assert.strictEqual(result[0][1], 'سطر اول داخل سلول\nسطر دوم داخل سلول\nسطر سوم');
    assert.strictEqual(result[0][2], 'پایان');
});

// 6. LF vs CRLF
runTest('Unit Test: پشتیبانی یکنواخت از هر دو نوع پایان سطر LF (\\n) و CRLF (\\r\\n)', () => {
    const inputLF = 'a,b,c\n1,2,3\n4,5,6';
    const inputCRLF = 'a,b,c\r\n1,2,3\r\n4,5,6';
    const resLF = parseCSV(inputLF);
    const resCRLF = parseCSV(inputCRLF);
    assert.deepStrictEqual(resLF, resCRLF);
    assert.strictEqual(resCRLF.length, 3);
    assert.deepStrictEqual(resCRLF[1], ['1', '2', '3']);
});

// 7. Malformed unclosed quote (MUST throw with line number)
runTest('Unit Test: کوتیشن بسته نشده باید خطای واضح با شماره سطر بدهد و بی سروصدا بسته نشود', () => {
    const malformedInput = '1,معتبر\n2,"سلول شروع شده اما بدون کوتیشن پایان\n3,ردیف دیگر';
    assert.throws(() => {
        parseCSV(malformedInput);
    }, (err) => {
        assert(err instanceof Error);
        assert(err.message.includes('سطر/رکورد تقریبی 2'), `پیام خطا باید شماره سطر تقریبی ۲ را داشته باشد. دریافت شد: ${err.message}`);
        return true;
    });
});

// 8. Strict RFC 4180 quote position: junk after closing quote ("x"junk,foo)
runTest('Unit Test: کاراکتر غیرمجاز پس از بسته‌شدن کوتیشن ("x"junk,foo) باید خطای صریح با شماره سطر بدهد', () => {
    assert.throws(() => {
        parseCSV('"x"junk,foo\n1,2');
    }, (err) => {
        assert(err instanceof Error);
        assert(err.message.includes('کاراکتر غیرمجاز پس از بسته‌شدن کوتیشن'));
        assert(err.message.includes('سطر/رکورد تقریبی 1'));
        return true;
    });
});

// 9. Strict RFC 4180 quote position: trailing chars after closing quote in column (a,"b"c)
runTest('Unit Test: کاراکتر غیرمجاز چسبیده به انتهای کوتیشن (a,"b"c) باید خطای صریح بدهد', () => {
    assert.throws(() => {
        parseCSV('a,"b"c\n1,2');
    }, (err) => {
        assert(err instanceof Error);
        assert(err.message.includes('کاراکتر غیرمجاز پس از بسته‌شدن کوتیشن'));
        return true;
    });
});

// 10. Strict RFC 4180 quote position: quote inside unquoted field (foo"bar,baz)
runTest('Unit Test: کوتیشن در میانهٔ فیلد بدون کوتیشن (foo"bar,baz) باید خطای صریح بدهد', () => {
    assert.throws(() => {
        parseCSV('foo"bar,baz\n1,2');
    }, (err) => {
        assert(err instanceof Error);
        assert(err.message.includes('کوتیشن فقط در ابتدای فیلد مجاز است'));
        return true;
    });
});

// 11. Empty lines
runTest('Unit Test: مدیریت سطرهای خالی (رد کردن پیش‌فرض یا حفظ در صورت درخواست)', () => {
    const inputWithEmpty = 'a,b\n\nc,d\n\ne,f';
    const skipped = parseCSV(inputWithEmpty, { skipEmptyLines: true });
    assert.strictEqual(skipped.length, 3);
    assert.deepStrictEqual(skipped, [['a', 'b'], ['c', 'd'], ['e', 'f']]);

    const preserved = parseCSV(inputWithEmpty, { skipEmptyLines: false });
    assert.strictEqual(preserved.length, 5);
    assert.deepStrictEqual(preserved[1], ['']);
});

// 12. Trailing newline at EOF (no phantom row)
runTest('Unit Test: کاراکتر Newline در انتهای فایل نباید سطر خالی مجازی اضافه کند', () => {
    const inputTrailingLF = 'col1,col2\nval1,val2\n';
    const inputTrailingCRLF = 'col1,col2\r\nval1,val2\r\n';
    const res1 = parseCSV(inputTrailingLF);
    const res2 = parseCSV(inputTrailingCRLF);
    assert.strictEqual(res1.length, 2);
    assert.strictEqual(res2.length, 2);
    assert.deepStrictEqual(res1, [['col1', 'col2'], ['val1', 'val2']]);
    assert.deepStrictEqual(res2, [['col1', 'col2'], ['val1', 'val2']]);
});

// 13. Preserving count and order of columns
runTest('Unit Test: حفظ دقیق تعداد و ترتیب ستون‌ها حتی در صورت وجود فیلدهای خالی', () => {
    const input = 'col1,col2,col3,col4\nval1,,val3,\n,val2,,val4';
    const result = parseCSV(input);
    assert.strictEqual(result.length, 3);
    assert.strictEqual(result[0].length, 4);
    assert.strictEqual(result[1].length, 4);
    assert.strictEqual(result[2].length, 4);
    assert.deepStrictEqual(result[0], ['col1', 'col2', 'col3', 'col4']);
    assert.deepStrictEqual(result[1], ['val1', '', 'val3', '']);
    assert.deepStrictEqual(result[2], ['', 'val2', '', 'val4']);
});

// 14. Preserving headers and column order on export
runTest('Unit Test: حفظ ترتیب و نام سرستون‌ها در خروجی نهایی final.csv (id, cleaned_text)', () => {
    const dataset = [
        ['id', 'cleaned_text'],
        [1, 'جمله اول پالایش‌شده'],
        [2, 'جمله دوم، حاوی کاما و "کوتیشن"']
    ];
    const csvOut = serializeCSV(dataset);
    assert(csvOut.startsWith('\uFEFF'));
    const reparsed = parseCSV(csvOut);
    assert.deepStrictEqual(reparsed, [
        ['id', 'cleaned_text'],
        ['1', 'جمله اول پالایش‌شده'],
        ['2', 'جمله دوم، حاوی کاما و "کوتیشن"']
    ]);
});

// 15. Round-Trip Test (serialize -> parse -> serialize -> parse)
runTest('Unit Test: آزمون رفت‌وبرگشت کامل (Round-trip) بدون جابه‌جایی یا از دست رفتن داده‌ها', () => {
    const complexData = [
        ['شناسه', 'عنوان', 'توضیحات چندسطری', 'برچسب'],
        ['101', 'متن با کاما، نقطه', 'سطر اول\nسطر دوم با "کوتیشن"', '#تست'],
        ['102', 'کتاب "کلیله و دمنه"', 'حاوی نیم‌فاصله‌ها: می\u200cشود و کتاب\u200cها', 'ادبی'],
        ['103', '', 'سلول خالی در عنوان', 'عادی']
    ];

    const serialized = serializeCSV(complexData);
    const parsed1 = parseCSV(serialized);
    assert.deepStrictEqual(parsed1, complexData);

    const serialized2 = serializeCSV(parsed1);
    const parsed2 = parseCSV(serialized2);
    assert.deepStrictEqual(parsed2, complexData);
});

// ----------------------------------------------------
// بخش ۲: آزمون‌های تابعی خط لوله مشترک (processCSV)
// ----------------------------------------------------

// 16. Functional Pipeline Test
runTest('Functional Test: آزمون خط لوله processCSV با پردازش رکوردهای چندستونی، حفظ نیولاین سلول و شناسه‌های اصلی', () => {
    const rawInputCSV =
`id,author,text,category
rec_101,علی,"متن اول، دارای کاما و
خط دوم درون همان سلول",ادبی
rec_102,سارا,"متن دوم با حروف عربي ك و ي و ايميل info@site.com",عمومی
rec_103,رضا,"ok",رد
rec_104,مریم,"این یک جملهٔ کاملاً معتبر و فارسی است.",علمی`;

    const result = processCSV(rawInputCSV, {
        hasHeader: true,
        textColumn: 2,
        idColumn: 0,
        preserveCellNewlines: true,
        cleanOptions: {
            normalizeChars: true,
            removeEmails: true,
            semiSpace: true,
            cleanPunctuation: true
        }
    });

    assert.strictEqual(result.rows.length, 3, 'باید ۳ رکورد معتبر باقی مانده باشد');
    assert.strictEqual(result.rows[0][0], 'rec_101');
    assert(result.rows[0][1].includes('\n'), 'کاراکتر newline درون سلول باید حفظ شود');
    assert(result.rows[0][1].includes('کاما'), 'کاما درون سلول حفظ شده است');
    assert.strictEqual(result.rows[1][0], 'rec_102');
    assert(!result.rows[1][1].includes('info@site.com'), 'ایمیل باید حذف شده باشد');
    assert(result.rows[1][1].includes('ک و ی'), 'حروف عربی باید به فارسی تبدیل شده باشند');
    assert.strictEqual(result.rows[2][0], 'rec_104');
});

// 17. Functional Auto-ID Pipeline Test
runTest('Functional Test: آزمون خط لوله processCSV با حالت «شناسه ندارد؛ شماره‌گذاری خودکار» و عدم فرض خودکار ستون اول به عنوان ID', () => {
    const rawNoIdCSV =
`comment,city
"این یک متن فارسی زیبا درباره شهر است.",اصفهان
"کوتاه",شیراز
"یک متن معتبر دیگر برای بررسی شماره‌گذاری خودکار.",تبریز`;

    const result = processCSV(rawNoIdCSV, {
        hasHeader: true,
        textColumn: 0,
        idColumn: 'auto'
    });

    assert.strictEqual(result.rows.length, 2);
    assert.strictEqual(result.rows[0][0], '1');
    assert.strictEqual(result.rows[1][0], '2');
});

// 18. Functional Error Handling
runTest('Functional Test: آزمون خط لوله processCSV در صورت کوتیشن بسته نشده باید مانع پردازش شود و شماره سطر را گزارش کند', () => {
    const malformed = 'id,text\n1,"متن سالم"\n2,"متن ناقص بدون کوتیشن پایان';
    assert.throws(() => {
        processCSV(malformed, { hasHeader: true, textColumn: 1, idColumn: 0 });
    }, (err) => {
        assert(err.message.includes('سطر/رکورد تقریبی 3'));
        return true;
    });
});

// 19. Functional Error Handling: Missing Text Column
runTest('Functional Test: آزمون خط لوله processCSV در صورت مشخص نبودن ستون متن باید خطای صریح بدهد بدون حدس خودکار', () => {
    const input = 'colA,colB\n1,سلام';
    assert.throws(() => {
        processCSV(input, { textColumn: -1 });
    }, (err) => {
        assert(err.message.includes('ستون متن برای پالایش مشخص نشده است'));
        return true;
    });
});

// ----------------------------------------------------
// بخش ۳: آزمون‌های مدیریت State و جلوگیری از خروجی Stale
// ----------------------------------------------------

// 20. Unit Test: Functional processing of edited strings
runTest('Unit Test: پردازش تابعی رشته‌های ویرایش‌شده در processCSV بدون نگه‌داشت داده‌های قبلی (محدودیت: این تست صرفاً منطق تابع خالص را می‌سنجد و رویدادهای زنده DOM مرورگر را پوشش نمی‌دهد)', () => {
    const initialCSV = 'id,text\n1,متن اولیه بدون ویرایش\n2,جمله دوم تست';
    const initialResult = processCSV(initialCSV, { hasHeader: true, textColumn: 1, idColumn: 0 });
    assert.strictEqual(initialResult.rows[0][1], 'متن اولیه بدون ویرایش');

    const editedCSV = 'id,text\n1,متن ویرایش‌شده توسط کاربر\n2,جمله دوم تست\n3,رکورد جدید اضافه شده در ادیتور';
    const editedResult = processCSV(editedCSV, { hasHeader: true, textColumn: 1, idColumn: 0 });

    assert.strictEqual(editedResult.rows.length, 3);
    assert.strictEqual(editedResult.rows[0][1], 'متن ویرایش‌شده توسط کاربر', 'خروجی باید متن جدید ویرایش‌شده را داشته باشد');
    assert.strictEqual(editedResult.rows[2][0], '3');
    assert.strictEqual(editedResult.rows[2][1], 'رکورد جدید اضافه شده در ادیتور');
});

// 21. Unit Test: State Clearing on input edit (Plain Text Workflow)
runTest('Unit Test: چرخهٔ کار متن ساده (Plain Text)؛ ویرایش ورودی باید state خروجی قبلی را پاک کرده و مانع دانلود stale شود', () => {
    const state = createInitialState();
    // Simulate successful run for plain text
    state.cleanedLines = ['جمله اول پاک‌سازی‌شده', 'جمله دوم پاک‌سازی‌شده'];
    state.cleanedText = 'جمله اول پاک‌سازی‌شده\nجمله دوم پاک‌سازی‌شده';

    // Verify initial exportable data exists
    assert.strictEqual(state.cleanedLines.length, 2);

    // User edits input: clearOutputState must be triggered
    clearOutputState(state);

    // Verify output state is completely emptied
    assert.strictEqual(state.cleanedLines.length, 0);
    assert.strictEqual(state.cleanedText, '');

    // Attempting export must be rejected
    const canExport = state.cleanedLines.length > 0 || state.cleanedRecords.length > 0;
    assert.strictEqual(canExport, false, 'خروجی نباید پیش از اجرای مجدد خط لوله قابل دانلود باشد');

    // Pipeline is re-run with new edited text
    const newText = 'متن جدید پس از ویرایش';
    const cleaned = cleanText(newText);
    state.cleanedLines = [cleaned];
    state.cleanedText = cleaned;

    assert.strictEqual(state.cleanedLines.length, 1);
    assert.strictEqual(state.cleanedLines[0], 'متن جدید پس از ویرایش');
});

// 22. Unit Test: State Clearing on input edit (CSV Workflow)
runTest('Unit Test: چرخهٔ کار فایل CSV؛ ویرایش ورودی یا بارگذاری جدید باید state خروجی قبلی را پاک کرده و مانع دانلود stale شود', () => {
    const state = createInitialState();
    state.isCsvMode = true;
    state.csvRawText = 'id,text\n1,این یک متن اولیه معتبر است';
    const run1 = processCSV(state.csvRawText, { hasHeader: true, textColumn: 1, idColumn: 0 });
    state.cleanedRecords = run1.rows;
    state.cleanedLines = run1.rows.map(r => r[1]);

    assert.strictEqual(state.cleanedRecords.length, 1);
    assert.strictEqual(state.cleanedRecords[0][1], 'این یک متن اولیه معتبر است');

    // User edits CSV in input box: clearOutputState is triggered immediately
    clearOutputState(state);

    // Verify output state is wiped
    assert.strictEqual(state.cleanedRecords.length, 0);
    assert.strictEqual(state.cleanedLines.length, 0);

    // Attempting export must be rejected
    const canExport = state.cleanedLines.length > 0 || state.cleanedRecords.length > 0;
    assert.strictEqual(canExport, false, 'در حالت ویرایش‌شده پیش از اجرای خط لوله دانلود باید غیرفعال باشد');

    // Pipeline is re-run with edited CSV
    const editedCsv = 'id,text\n1,این یک متن اصلاح‌شده جدید و معتبر است';
    const run2 = processCSV(editedCsv, { hasHeader: true, textColumn: 1, idColumn: 0 });
    state.cleanedRecords = run2.rows;
    state.cleanedLines = run2.rows.map(r => r[1]);

    assert.strictEqual(state.cleanedRecords.length, 1);
    assert.strictEqual(state.cleanedRecords[0][1], 'این یک متن اصلاح‌شده جدید و معتبر است');
});

// 23. Unit Test: Resetting CSV mode when switching to non-CSV inputs/actions
runTest('Unit Test: ریست کامل وضعیت CSV mode در صورت جابه‌جایی یا پاک‌سازی ورودی', () => {
    const testState = createInitialState();
    testState.isCsvMode = true;
    testState.csvRawText = 'id,text\n1,نمونه';
    testState.cleanedRecords = [['1', 'نمونه']];

    resetCsvState(testState);

    assert.strictEqual(testState.isCsvMode, false, 'isCsvMode باید false شود');
    assert.strictEqual(testState.csvRawText, '', 'csvRawText باید خالی شود');
    assert.deepStrictEqual(testState.cleanedRecords, [], 'cleanedRecords باید خالی شود');
});

// 24. Unit Test: Preserving manual ID column selection during text edits
runTest('Unit Test: بررسی رفتار تابع کمکی syncCsvIdSelection در حفظ انتخاب دستی شناسه (محدودیت: این تست صرفاً منطق تابع کمکی را می‌سنجد و انتخاب مستقیم UI را ارزیابی نمی‌کند، هرچند UI مستقیماً از همین تابع در syncCsvStateFromInput استفاده می‌کند)', () => {
    // 1. User previously had "auto" selected: must strictly remain "auto"
    assert.strictEqual(syncCsvIdSelection('auto', 4), 'auto', 'اگر کاربر auto انتخاب کرده باشد باید حتماً auto بماند');
    assert.strictEqual(syncCsvIdSelection('', 4), 'auto');

    // 2. User manually selected column 2: must strictly preserve column 2
    assert.strictEqual(syncCsvIdSelection('2', 4), '2', 'ستون انتخابی کاربر (ستون ۲) باید حفظ شود');

    // 3. If selected column no longer exists (e.g. column deleted during edit): falls back safely to auto
    assert.strictEqual(syncCsvIdSelection('3', 2), 'auto', 'اگر ستون حذف شده باشد باید به auto بازگردد');
});

// 25. Unit Test: Option change clears previous output state to prevent stale export
runTest('Unit Test: تغییر هریک از گزینه‌های تنظیمات (مانند csvHasHeader, csvTextCol, csvIdCol یا گزینه‌های پاک‌سازی) باید بلافاصله خروجی قبلی را پاک کرده و مانع دانلود دادهٔ Stale شود', () => {
    const state = createInitialState();
    // Simulate successful run with output data
    state.cleanedLines = ['متن پالایش‌شده'];
    state.cleanedRecords = [['1', 'متن پالایش‌شده']];

    // User changes a cleaning toggle (e.g. turns off normalizeChars)
    updateConfigOption(state, 'normalizeChars', false);

    // Verify output is instantly invalidated and emptied
    assert.strictEqual(state.cleanedLines.length, 0, 'cleanedLines باید بلافاصله خالی شود');
    assert.strictEqual(state.cleanedRecords.length, 0, 'cleanedRecords باید بلافاصله خالی شود');

    // Verify export is refused
    const canExportAfterToggle = state.cleanedLines.length > 0 || state.cleanedRecords.length > 0;
    assert.strictEqual(canExportAfterToggle, false, 'پس از تغییر گزینه نباید دانلود داده‌های قبلی ممکن باشد');

    // User changes CSV column selection (e.g. changes textColumn)
    state.cleanedRecords = [['1', 'متن قبلی']];
    updateConfigOption(state, 'textColumn', 2);
    assert.strictEqual(state.cleanedRecords.length, 0, 'با تغییر ستون متن نیز باید خروجی بلافاصله پاک شود');
});

// 26. Unit Test: Comprehensive wipe of all output-dependent stats (avgSentenceLength, avgWordLength, hashtags)
runTest('Unit Test: پاک‌سازی جامع تمامی فیلدهای آماری وابسته به خروجی (avgSentenceLength, avgWordLength, hashtags و فرکانس‌ها) در clearOutputState و جلوگیری از تولید گزارش منسوخ', () => {
    const state = createInitialState();
    // Simulate populated output metrics from previous run
    state.cleanedLines = ['جمله اول با هشتگ #پروژه', 'جمله دوم پالایش‌شده'];
    state.cleanedRecords = [['1', 'جمله اول با هشتگ #پروژه'], ['2', 'جمله دوم پالایش‌شده']];
    state.stats.cleanChars = 45;
    state.stats.cleanWords = 8;
    state.stats.cleanLines = 2;
    state.stats.avgSentenceLength = 4.0;
    state.stats.avgWordLength = 5.2;
    state.stats.hashtags = { '#پروژه': 1 };
    state.stats.wordFrequencies = { 'جمله': 2, 'اول': 1 };
    state.stats.charFrequencies = { 'ج': 2, 'م': 2 };

    // Trigger clearOutputState
    clearOutputState(state);

    // Verify output metrics are completely wiped
    assert.strictEqual(state.stats.cleanChars, 0);
    assert.strictEqual(state.stats.cleanWords, 0);
    assert.strictEqual(state.stats.cleanLines, 0);
    assert.strictEqual(state.stats.avgSentenceLength, 0, 'میانگین طول جمله باید صفر شود');
    assert.strictEqual(state.stats.avgWordLength, 0, 'میانگین طول کلمه باید صفر شود');
    assert.deepStrictEqual(state.stats.hashtags, {}, 'آمار هشتگ‌ها باید کاملاً خالی شود');
    assert.deepStrictEqual(state.stats.wordFrequencies, {});
    assert.deepStrictEqual(state.stats.charFrequencies, {});
    assert.deepStrictEqual(state.cleanedLines, []);
    assert.deepStrictEqual(state.cleanedRecords, []);

    // Verify report export refusal
    const canExportReport = state.cleanedLines.length > 0 || state.cleanedRecords.length > 0;
    assert.strictEqual(canExportReport, false, 'تولید یا دانلود گزارش analyzer.txt پس از پاک‌سازی state باید ناممکن باشد');
});

console.log('\n-----------------------------------------------------');
console.log(`نتیجه کلی آزمون‌ها: ${passedTests} از ${totalTests} با موفقیت سپری شد.`);
console.log('-----------------------------------------------------\n');
