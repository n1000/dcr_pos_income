#!/usr/bin/env python3
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
from datetime import datetime, timezone
import json
import logging
import subprocess

default_format_mode = 'verbose'
default_csv_prices_file = 'dcr_prices.csv'
default_transactions_file = 'all_transactions.json'

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
        # TODO: enhance output, or remove sanity check
        raise RuntimeError('TXID returned by dcrctl is not as expected!')

    return tx_contents

def get_block_hash(block_num):
    r = exec_cmd(['dcrctl', 'getblockhash', str(block_num)])

    return r.stdout.strip()

def get_block_header(block_hash):
    r = exec_cmd(['dcrctl', 'getblockheader', block_hash])
    header = json.loads(r.stdout)

    if header['hash'] != block_hash:
        # TODO: enhance output, or remove sanity check
        raise RuntimeError('Block header returned by dcrctl is not as expected!')

    return header

def get_block_time(block_num):
    block_hash = get_block_hash(block_num)
    header = get_block_header(block_hash)

    return header['time']

def load_prices(filename):
    # db is [ ('date_str', price), ... ]
    db = []
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            db += [ (r['date'], r['price(USD)']) ]

    return db

def get_days_price(db, date):
    utc_date = date.astimezone(timezone.utc)
    utc_date_str = utc_date.strftime('%Y-%m-%d')

    for (d, p) in db:
        if d == utc_date_str:
            return float(p)

    raise RuntimeError('Could not find date {} in price database!'.format(utc_date_str))

def main():
    logging.basicConfig(level=logging.ERROR)

    parser = argparse.ArgumentParser(description='Calculate Decred PoS Income Details')

    last_year = str(datetime.now().year - 1)
    default_first_date = last_year + '-01-01'
    default_last_date = last_year + '-12-31'

    parser.add_argument('--first_date', default=default_first_date,
        help='beginning of time period (default: {})'.format(default_first_date))
    parser.add_argument('--last_date', default=default_last_date,
        help='end of time period (default: {})'.format(default_last_date))
    parser.add_argument('--format', dest='format_mode', default=default_format_mode,
        help='select output format: verbose, compact (default: {})'.format(default_format_mode))
    parser.add_argument('--prices', dest='csv_prices_file', default=default_csv_prices_file,
        help='DCR CSV prices file (default: {})'.format(default_csv_prices_file))
    parser.add_argument('--tx_file', dest='transactions_file', default=default_transactions_file,
        help='DCR transactions file (default: {})'.format(default_transactions_file))

    args = parser.parse_args()

    if args.format_mode != 'verbose' and args.format_mode != 'compact':
        logging.info('invalid format_mode given, defaulting to verbose')
        args.format_mode = 'verbose'

    first_date = datetime.strptime(args.first_date, '%Y-%m-%d').astimezone()
    last_date = datetime.strptime(args.last_date, '%Y-%m-%d').astimezone()

    prices = load_prices(args.csv_prices_file)

    income_dcr = 0
    income_usd = 0
    fees_dcr = 0
    fees_usd = 0

    with open(args.transactions_file, mode='r') as json_file:
        tx_db = json.load(json_file)

    for r in tx_db:
        utc_tstamp = int(r['blocktime'])

        tx_date = datetime.fromtimestamp(utc_tstamp, timezone.utc)
        local_tx_date_str = tx_date.astimezone().strftime('%Y-%m-%d')

        if tx_date < first_date or tx_date > last_date:
            logging.debug('skipping out of range date: {}'.format(local_tx_date_str))
            continue

        if r['txtype'] == 'vote' and r['vout'] == 0:
            p_vday = get_days_price(prices, tx_date)

            logging.debug('Date: {}, Price: {:.02f}, Blocktime: {}'.format(local_tx_date_str, p_vday, utc_tstamp))

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
            ticket_date = datetime.fromtimestamp(ticket_block_time, timezone.utc)
            local_ticket_date_str = ticket_date.astimezone().strftime('%Y-%m-%d')

            p_tday = get_days_price(prices, ticket_date)

            # get fee details from ticket purchase
            ticket_tx_contents = get_decoded_tx(tx_contents['vin'][1]['txid'])

            cur_dcr_fee = ticket_tx_contents['vin'][0]['amountin'] - ticket_tx_contents['vout'][0]['value']
            cur_usd_fee = cur_dcr_fee * p_tday

            fees_dcr += cur_dcr_fee
            fees_usd += cur_usd_fee

            if args.format_mode == 'compact':
                print('Date: {}, Income: {:.02f} USD, Fee: {:.02f} USD'.format(local_tx_date_str, cur_usd_income, cur_usd_fee))
            elif args.format_mode == 'verbose':
                print('Vote: [Date: {}, Income: {:.04f} DCR x {:.02f} USD/DCR = {:.02f} USD] Fee: [Date: {}, {:.04f} DCR x {:.02f} USD/DCR = {:.02f} USD]'.format(local_tx_date_str, cur_dcr_income, p_vday, cur_usd_income, local_ticket_date_str, cur_dcr_fee, p_tday, cur_usd_fee))

    print('\nTotal Income: DCR: {:.04f}, USD: {:.02f}'.format(income_dcr, income_usd))
    print('Total Fees: DCR: {:.04f}, USD: {:.02f}'.format(fees_dcr, fees_usd))

if __name__ == '__main__':
    main()
