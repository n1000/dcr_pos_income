# dcr_pos_income.py -- Calculate Decred PoS Income Details

This is a small python script that can help calculate the PoS income
that has occured over a particular time period.

The inputs are:

* A transaction file, dumped from your Decred wallet

* Blockchain transaction details, accessed automatically via dcrctl

* A Decred price database file

## Limitations

* Currently assumes USD currency

* Somewhat slow (due to all the dcrctl queries)

## Setup Steps / Prerequisites

1. Save all transactions to a file:
    ```
    dcrctl --wallet listtransactions '*' 999999 0 false > all_transactions.json
    ```
2. Download a DCR prices data base from [here](https://coinmetrics.io/data-downloads/) ([direct link]()):
    ```
    wget -O dcr_prices.csv https://coinmetrics.io/data/dcr.csv
    ```

## Basic Usage

```
python3 dcr_pos_income.py
```

## Command Line Help
```
usage: dcr_pos_income.py [-h] [--first_date FIRST_DATE] [--last_date LAST_DATE]
                     [--format FORMAT_MODE]

Calculate Decred PoS Income Details

optional arguments:
  -h, --help            show this help message and exit
  --first_date FIRST_DATE
                        beginning of time period
  --last_date LAST_DATE
                        end of time period
  --format FORMAT_MODE  select output format: verbose, compact

```

## Example output

1. Verbose output:
```
$ ./dcr_pos_income.py --format verbose --first_date "2017-04-22" --last_date "2017-05-10"
Vote: [Date: 2017-04-22, Income: 1.5340 DCR x 14.89 USD/DCR = 22.84 USD] Fee: [Date: 2017-03-29, 0.0116 DCR x 12.99 USD/DCR = 0.15 USD]
Vote: [Date: 2017-04-22, Income: 1.5340 DCR x 14.89 USD/DCR = 22.84 USD] Fee: [Date: 2017-03-05, 0.0030 DCR x 2.14 USD/DCR = 0.01 USD]
Vote: [Date: 2017-04-23, Income: 1.5340 DCR x 14.77 USD/DCR = 22.66 USD] Fee: [Date: 2017-02-25, 0.0030 DCR x 2.28 USD/DCR = 0.01 USD]
Vote: [Date: 2017-04-29, Income: 1.5340 DCR x 15.33 USD/DCR = 23.52 USD] Fee: [Date: 2017-03-05, 0.0030 DCR x 2.14 USD/DCR = 0.01 USD]
Vote: [Date: 2017-05-02, Income: 1.5188 DCR x 14.94 USD/DCR = 22.69 USD] Fee: [Date: 2017-03-12, 0.0058 DCR x 3.28 USD/DCR = 0.02 USD]
Vote: [Date: 2017-05-05, Income: 1.5188 DCR x 15.33 USD/DCR = 23.28 USD] Fee: [Date: 2017-04-28, 0.0238 DCR x 14.55 USD/DCR = 0.35 USD]
Vote: [Date: 2017-05-08, Income: 1.5188 DCR x 17.24 USD/DCR = 26.18 USD] Fee: [Date: 2017-04-28, 0.0277 DCR x 14.55 USD/DCR = 0.40 USD]
Vote: [Date: 2017-05-09, Income: 1.5188 DCR x 17.23 USD/DCR = 26.17 USD] Fee: [Date: 2017-04-28, 0.0238 DCR x 14.55 USD/DCR = 0.35 USD]
Vote: [Date: 2017-05-09, Income: 1.5188 DCR x 17.23 USD/DCR = 26.17 USD] Fee: [Date: 2017-05-07, 0.0299 DCR x 17.03 USD/DCR = 0.51 USD]

Total Income: DCR: 13.7299, USD: 216.35
Total Fees: DCR: 0.1315, USD: 1.79

```

2. Compact output:
```
$ ./dcr_pos_income.py --format compact --first_date "2017-04-22" --last_date "2017-05-10"
Date: 2017-04-22, Income: 22.84 USD, Fee: 0.15 USD
Date: 2017-04-22, Income: 22.84 USD, Fee: 0.01 USD
Date: 2017-04-23, Income: 22.66 USD, Fee: 0.01 USD
Date: 2017-04-29, Income: 23.52 USD, Fee: 0.01 USD
Date: 2017-05-02, Income: 22.69 USD, Fee: 0.02 USD
Date: 2017-05-05, Income: 23.28 USD, Fee: 0.35 USD
Date: 2017-05-08, Income: 26.18 USD, Fee: 0.40 USD
Date: 2017-05-09, Income: 26.17 USD, Fee: 0.35 USD
Date: 2017-05-09, Income: 26.17 USD, Fee: 0.51 USD

Total Income: DCR: 13.7299, USD: 216.35
Total Fees: DCR: 0.1315, USD: 1.79
```

## License

Copyright (c) 2018 Nathaniel Houghton <nathan@brainwerk.org>

Permission to use, copy, modify, and distribute this software for
any purpose with or without fee is hereby granted, provided that
the above copyright notice and this permission notice appear in all
copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA
OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.