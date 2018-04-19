#!/usr/local/bin/python3
#
# Copyright (c) 2018 Nathaniel Houghton <nathan@brainwerk.org>
#
# Permission to use, copy, modify, and distribute this software for
# any purpose with or without fee is hereby granted, provided that
# the above copyright notice and this permission notice appear in all
# copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
# AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
# DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA
# OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

import argparse
import csv
from datetime import datetime
import json
import logging
import math

csv_prices_file = "dcr_prices.csv"

def load_prices(filename):
    # db is [ ('date_str', price), ... ]
    db = []
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            db += [ (r['date'], r['price(USD)']) ]

    return db

def get_days_price(db, date_str):
    for (d, p) in db:
        if d == date_str:
            return float(p)

    raise RuntimeError('Could not find date {} in price database!'.format(date_str))

def estimate_total_subsidy(blockheight):
    base_subsidy = 3119582664
    mul_subsidy = 100
    div_subsidy = 101
    subsidy_red_interval = 6144

    cur_subsidy = base_subsidy
    reduction_cnt = blockheight // subsidy_red_interval
    for i in range(reduction_cnt):
        cur_subsidy = math.floor(cur_subsidy * mul_subsidy)
        cur_subsidy = cur_subsidy // div_subsidy

    return cur_subsidy

def estimate_vote_subsidy(total_subsidy):
    work_reward_prop = 6
    stake_reward_prop = 3
    block_tax_prop = 1
    votes_per_block = 5

    vote_subsidy = total_subsidy * 3 / 10 / votes_per_block

    return vote_subsidy

def main():
    logging.basicConfig(level=logging.ERROR)

    parser = argparse.ArgumentParser(description='Calculate PoS Tax Details')

    # to do -- by default, use the last year for computation
    # to do -- to determine the fee, we may actually have to start before
    # the start date, to look up the fee for buying the ticket
    parser.add_argument('--first_date', default='2015-01-01',
        help='Beginning of time period')
    parser.add_argument('--last_date', default='2017-01-01',
        help='End of time period')

    args = parser.parse_args()

    # to do -- try to parse these here, and convert to datetime object?
    first_date = datetime.strptime(args.first_date, '%Y-%m-%d')
    last_date = datetime.strptime(args.last_date, '%Y-%m-%d')

    prices = load_prices(csv_prices_file)

    total_subsidy = estimate_total_subsidy(227328)
    vote_subsidy = estimate_vote_subsidy(total_subsidy)

    income_dcr = 0
    income_usd = 0
    fees_dcr = 0
    fees_usd = 0

    with open('all_transactions.json', mode='r') as json_file:
        tx_db = json.load(json_file)

    with open('hashmap.json', mode='r') as json_file:
        hashmap_db = json.load(json_file)

    for r in tx_db:
        utc_tstamp = int(r['blocktime'])

        date = datetime.fromtimestamp(utc_tstamp)
        price_date = date.strftime('%Y-%m-%d')

        if date < first_date or date > last_date:
            logging.debug('skipping out of range date: {}'.format(price_date))
            continue

        p = get_days_price(prices, price_date)

        if r['txtype'] == 'vote' and r['vout'] == 0:
            logging.debug('Date: {}, Price: {:.02f}, Blocktime: {}'.format(price_date, p, utc_tstamp))

            blockheight = hashmap_db[r['blockhash']]

            subsidy = estimate_vote_subsidy(estimate_total_subsidy(blockheight)) / 1e8

            cur_dcr_income = subsidy
            cur_usd_income = subsidy * p

            income_dcr += cur_dcr_income
            income_usd += cur_usd_income

            print('Vote: Date: {}, DCR: {:.04f}, USD: {:.02f}, Day\'s Price: {:.02f}'.format(price_date, cur_dcr_income, cur_usd_income, p))

        if r['txtype'] == 'ticket' and r['vout'] == 1:
            cur_dcr_fee = abs(float(r['fee']))
            cur_usd_fee = cur_dcr_fee * p

            fees_dcr += cur_dcr_fee
            fees_usd += cur_usd_fee

            print('Purchase Fee: Date: {} DCR: {:.04f}, USD: {:.02f}, Day\'s Price: {:.02f}'.format(price_date, cur_dcr_fee, cur_usd_fee, p))

    print('Total Income: DCR: {:.04f}, USD: {:.02f}'.format(income_dcr, income_usd))
    print('Total Fees: DCR: {:.04f}, USD: {:.02f}'.format(fees_dcr, fees_usd))

if __name__ == '__main__':
    main()
