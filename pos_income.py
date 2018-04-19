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
import subprocess

def exec_cmd(cmd):
    return subprocess.run(cmd, check=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def get_raw_tx(txid):
    r = exec_cmd(['dcrctl', 'getrawtransaction', txid])

    return r.stdout.strip()

def get_decoded_tx(txid):
    raw_tx = get_raw_tx(txid)

    r = exec_cmd(['dcrctl', 'decoderawtransaction', raw_tx])
    tx_contents = json.loads(r.stdout)

    if tx_contents['txid'] != txid:
        # todo: enhance output, or remove sanity check
        raise RuntimeError('TXID returned by dcrctl is not as expected!')

    return tx_contents

def get_block_hash(block_num):
    r = exec_cmd(['dcrctl', 'getblockhash', str(block_num)])

    return r.stdout.strip()

def get_block_header(block_hash):
    r = exec_cmd(['dcrctl', 'getblockheader', block_hash])
    header = json.loads(r.stdout)

    if header['hash'] != block_hash:
        # todo: enhance output, or remove sanity check
        raise RuntimeError('Block header returned by dcrctl is not as expected!')

    return header

def get_block_time(block_num):
    block_hash = get_block_hash(block_num)
    header = get_block_header(block_hash)

    return header['time']

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

    income_dcr = 0
    income_usd = 0
    fees_dcr = 0
    fees_usd = 0

    with open('all_transactions.json', mode='r') as json_file:
        tx_db = json.load(json_file)

    for r in tx_db:
        utc_tstamp = int(r['blocktime'])

        tx_date = datetime.fromtimestamp(utc_tstamp)
        tx_date_str = tx_date.strftime('%Y-%m-%d')

        if tx_date < first_date or tx_date > last_date:
            logging.debug('skipping out of range date: {}'.format(tx_date_str))
            continue

        if r['txtype'] == 'vote' and r['vout'] == 0:
            p_vday = get_days_price(prices, tx_date_str)

            logging.debug('Date: {}, Price: {:.02f}, Blocktime: {}'.format(tx_date_str, p_vday, utc_tstamp))

            tx_contents = get_decoded_tx(r['txid'])
            subsidy = tx_contents['vin'][0]['amountin']

            cur_dcr_income = subsidy
            cur_usd_income = subsidy * p_vday
            income_dcr += cur_dcr_income
            income_usd += cur_usd_income

            # ticket block number, needed to get block timestamp
            ticket_block = tx_contents['vin'][1]['blockheight']

            # get tickets block, to get timestamp
            ticket_block_time = get_block_time(ticket_block)

            # get price based on timestamp
            ticket_date = datetime.fromtimestamp(ticket_block_time)
            ticket_date_str = ticket_date.strftime('%Y-%m-%d')
            p_tday = get_days_price(prices, ticket_date_str)

            # get fee details from ticket purchase
            ticket_tx_contents = get_decoded_tx(tx_contents['vin'][1]['txid'])

            cur_dcr_fee = ticket_tx_contents['vin'][0]['amountin'] - ticket_tx_contents['vout'][0]['value']
            cur_usd_fee = cur_dcr_fee * p_tday

            fees_dcr += cur_dcr_fee
            fees_usd += cur_usd_fee

            print('Vote: Date: {}, DCR: {:.04f}, USD: {:.02f}, Day\'s Price: {:.02f}'.format(tx_date_str, cur_dcr_income, cur_usd_income, p_vday))
            print('Purchase Fee: Date: {} DCR: {:.04f}, USD: {:.02f}, Day\'s Price: {:.02f}'.format(ticket_date_str, cur_dcr_fee, cur_usd_fee, p_tday))

    print('Total Income: DCR: {:.04f}, USD: {:.02f}'.format(income_dcr, income_usd))
    print('Total Fees: DCR: {:.04f}, USD: {:.02f}'.format(fees_dcr, fees_usd))

if __name__ == '__main__':
    main()
