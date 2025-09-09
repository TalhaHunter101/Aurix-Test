We need to build a new app for Argos SmartSuite, but before I want to
run a test to see if I can perform this task entirely with AI.

At the moment we are performing this project in a Gsheet. Here for your
reference:
spam_pilot_100_feedback x linguist.csv

My idea is to create a script that performs the task for us.

**INSTRUCTIONS FOR PROMPT**

1.  Column E - Read the content and answer YES or NO taking into account
    the following question: Is there any Key Word Spam in the content?

2.  Column F - Read the content and answer YES or NO taking into account
    the following question: Is there any Malicious Links in the content?

3.  Column G - Read the content and answer YES or NO taking into account
    the following question: Is there any Advertisements in the content?

4.  Column H - Reading the entire content, the content is not in the
    target language. Yes or No?

5.  Column I - Reading the entire content, the content is not readable
    or is incomprehensible. Yes or No?

Here you have the various prompt for each column:

**PROMPT FOR COLUMN E**

Reading the entire content, is there any Key Word Spam in the text?
Yes/No

Keyword spam involves the intentional placement of certain words on a
web page to influence search engines or other websites that index the
page. These terms will have little to no connection to the content of a
page, these terms are used simply to attract more traffic to the
website. These keywords may appear many times one after another, or
appear in a list or group. You can identify this keyword spam by looking
for repeated terms that appear out of context; unrelated to the text
content on the page. If you see certain terms repeated many times in
this manner, please select this category in your annotation.

Examples:

"Our site provides you with more streams and more links to see Catanzaro
vs Lecce game than any other website. And now you can enjoy the
Catanzaro vs Lecce live telecast stream. Enjoy watching Catanzaro vs
Lecce online game using our live online streaming. If You are looking
for watch online stream Lecce, watch online stream Catanzaro,
livestreaming Lecce, live streaming Catanzaro, live stream Lecce, live
stream Catanzaro\..."

Answer: Yes

**PROMPT FOR COLUMN F**

Reading the entire content, is there any Malicious Links in the text?
Yes/No

You should answer Yes if you see a document contains an external link
that's obviously intended to deceive visitors to the web page. A
deceptive web page will often suggest that if a visitor clicks on a link
that they will win money, some prize, or be able to view exclusive
content, but the real aim is to exploit the visitors to the website.
This includes suspected "phishing", where a visitor is tricked into
revealing information like their login name and password, or financial
information like accredit card number. Use your best judgment when
comparing an external link to the content of a document: if you believe
an external link is intended to solicit the reader's personal or
financial information please select this category in your annotation.

Examples:

1.  "You're the 1 millionth visitor to this website! Click here to win a
    free iPad!"

Answer: Yes

Explanation: Here a malicious link to steal the reader's personal
information is disguised as an enticing offer to win a prize.

**PROMPT FOR COLUMN G**

Reading the entire content, is there any Advertisements in the text?
Yes/No

We consider advertisements to be language within the text of a web page
that encourage the reader to buy or use any product or service.
Solicitation that encourages the reader to visit a business or download
an app, as well as "want ads" looking for applicants to perform a job or
service are also considered to be advertisements.

Note that if the text describes a product and contains useful
information about its specifications we do not consider this to be
advertising and you should not select Yes in your annotation.

Examples:

"Cozy Inn \$99 (\$247). Excellent location close to the water. Walk to
restaurants and the beach. This deal won't last, click here to book
now!"

Answer: Yes

**PROMPT FOR COLUMN H -** *In case the answer to this question is YES,
all other answers to all questions should be NO.*

Reading the entire content, the content is not in the target language.
Yes or No?

The text documents should be in English.

1.  Answer YES if the content is not in English and only contains text
    in another language

2.  Answer NO if the content is in English and only contains a small
    amount of text in another language, but is otherwise in English

**PROMPT FOR COLUMN I -** *In case the answer to this question is YES,
all other answers to all questions should be NO.*

Read the content and answer the question: Is the content not readable or
incomprehensible. Some contents may be mal-encoded (where text may
appear as strange characters like \"ÃƒÆ\"), entirely missing (e.g. a
blank document ""), or otherwise unreadable. In these cases:

1.  Answer YES if the content is unreadable or if the text file is
    entirely empty or you cannot open the document due to some error

2.  Answer NO if the content is readable and there is any amount of
    readable text in English

**PROMPT FOR COLUMN J**

How confident are you with the answers provided? Give me a score from 1
to 5 where 1 is the lowest confidence and 5 is the highest.

**OUTPUT JSON**

The client passed us a very detailed schema.

{\"uid\": \"d6727150-e233-427c-bbca-55cd64230fdb\", - this is the uid
passed from the client

\"content\": \"Text for document 1\",

\"labels_spam\": 0 - this value changes from 0 to 1 according to the
labels_spam_vector values; if only one of the labels_spam_vector value
is 1, this should be 1. Vice versa, if labels_spam_vector values are all
0, this should be 0.

\"labels_spam_vector\":

{\"keyword_spam\": 0, - 0 in our Gsheet is NO, while 1 is YES; this is
applicable to the rest

\"malicious_links\": 0,

\"ads\": 0,

\"\"wrong_language\": 1 - this value and item should be present only if
the answer in column H of our sheet is YES, and the value it\'s always
1; otherwise this should not be present at all\"

\"unreadable\": 1 - this value and item should be present only if the
answer in column I of our sheet is YES, and the value it\'s always 1;
otherwise this should not be present at all

}}

Attached you will find:

-   a sample delivery file called \"spam_pilot_100_key.jsonl\"

-   a CSV with correct answers in order to check if the AI results
    match/are correct
