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
import tempfile
import sys
import os

default_format_mode = 'verbose'
default_csv_prices_file = 'dcr_prices.csv'
default_transactions_file = 'all_transactions.json'
default_first_date = '1900-01-01'
default_last_date = '9999-12-31'
default_cache_file = 'dcrctl.cache'

class dcrctl_cli:
    cache_version = 1
    unflushed_cache_cnt = 0
    max_unflushed = 10

    def exec_cmd(self, cmd_args):
        r = self.get_cache(cmd_args)
        if r != None:
            return r

        cmd = ['dcrctl'] + cmd_args

        r = subprocess.run(cmd, check=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.add_cache(cmd_args, r.stdout)

        return r.stdout

    # these functions interact with dcrctl
    def getrawtransaction(self, txid):
        r = self.exec_cmd(['getrawtransaction', txid])

        return r.strip()

    def decoderawtransaction(self, raw_tx):
        r = self.exec_cmd(['decoderawtransaction', raw_tx])
        tx_contents = json.loads(r)

        return tx_contents

    def getblockhash(self, block_num):
        r = self.exec_cmd(['getblockhash', str(block_num)])

        return r.strip()

    def getblockheader(self, block_hash):
        r = self.exec_cmd(['getblockheader', block_hash])
        header = json.loads(r)

        return header

    # helper functions that combine above operations
    def get_decoded_tx(self, txid):
        raw_tx = self.getrawtransaction(txid)
        tx_contents = self.decoderawtransaction(raw_tx)

        return tx_contents

    def get_block_time(self, block_num):
        block_hash = self.getblockhash(block_num)
        header = self.getblockheader(block_hash)

        return header['time']

    # cache related utilities
    def load_cache(self):
        if self.no_cache:
            return

        try:
            with open(self.cache_filename, mode='r') as json_file:
                self.cache = json.load(json_file)
        except FileNotFoundError as e:
            print('info: {} not found, using empty cache'.format(self.cache_filename), file=sys.stderr)
            self.cache = { 'cache_version': self.cache_version }

        if self.cache['cache_version'] != self.cache_version:
            print('info: unexpected cache version {} (expected {}), replacing'.format(self.cache['cache_version'], self.cache_version), file=sys.stderr)
            self.cache = { 'cache_version': self.cache_version }

    def save_cache(self):
        if self.no_cache:
            return

        cache_file_dir = os.path.dirname(self.cache_filename)
        temp_out = tempfile.NamedTemporaryFile(mode='w+', delete=False, dir=cache_file_dir)
        json.dump(self.cache, temp_out)
        os.rename(temp_out.name, self.cache_filename)

    def cachable(self, cmd_args):
        # currently we only cache command output for 2 arg commands
        if len(cmd_args) == 2:
            return True

        return False

    def get_cache(self, cmd_args):
        if self.no_cache:
            return None

        if not self.cachable(cmd_args):
            return None

        cmd_type = str(cmd_args[0])
        cmd_arg1 = str(cmd_args[1])

        if cmd_type not in self.cache:
            return None

        if cmd_arg1 in self.cache[cmd_type]:
            return self.cache[cmd_type][cmd_arg1]

        return None

    def add_cache(self, cmd_args, result):
        if self.no_cache:
            return

        if not self.cachable(cmd_args):
            return

        # already cached
        if self.get_cache(cmd_args) != None:
            return

        cmd_type = str(cmd_args[0])
        cmd_arg1 = str(cmd_args[1])

        if cmd_type not in self.cache:
            self.cache[cmd_type] = {}

        self.cache[cmd_type][cmd_arg1] = result

        self.unflushed_cache_cnt += 1
        if self.unflushed_cache_cnt >= self.max_unflushed:
            self.save_cache()
            self.unflushed_cache_cnt = 0

    def shutdown(self):
        if self.unflushed_cache_cnt != 0:
            self.save_cache()
            self.unflushed_cache_cnt = 0

    def __init__(self, no_cache=False, cache_filename='dcrctl.cache', max_unflushed=10):
        self.cache_filename = cache_filename
        self.max_unflushed = max_unflushed
        self.no_cache = no_cache

        self.load_cache()

def load_prices(filename):
    db = {}
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            try:
                db[r['date']] = float(r['price(USD)'])
            except ValueError:
                # skip invalid price values
                continue

    return db

def get_days_price(db, date):
    utc_date = date.astimezone(timezone.utc)
    utc_date_str = utc_date.strftime('%Y-%m-%d')

    if utc_date_str in db:
        return db[utc_date_str]

    raise RuntimeError('Could not find date {} in price database!'.format(utc_date_str))

def main():
    logging.basicConfig(level=logging.ERROR)

    parser = argparse.ArgumentParser(description='Calculate Decred PoS Income Details')

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
    parser.add_argument('--no_cache', dest='no_cache',
        action='store_true', help='disable dcrctl output caching')
    parser.add_argument('--cache_file', dest='cache_file', default=default_cache_file,
        help='select dcrctl cache file (default: {})'.format(default_cache_file))

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

    dcrctl = dcrctl_cli(no_cache=args.no_cache, cache_filename=args.cache_file)

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

            tx_contents = dcrctl.get_decoded_tx(r['txid'])
            subsidy = tx_contents['vin'][0]['amountin']

            cur_dcr_income = subsidy
            cur_usd_income = subsidy * p_vday
            income_dcr += cur_dcr_income
            income_usd += cur_usd_income

            # ticket block number, needed to get block timestamp
            ticket_block = tx_contents['vin'][1]['blockheight']

            # get tickets block, to get timestamp
            ticket_block_time = dcrctl.get_block_time(ticket_block)

            # get price based on timestamp
            ticket_date = datetime.fromtimestamp(ticket_block_time, timezone.utc)
            local_ticket_date_str = ticket_date.astimezone().strftime('%Y-%m-%d')

            p_tday = get_days_price(prices, ticket_date)

            # get fee details from ticket purchase
            ticket_tx_contents = dcrctl.get_decoded_tx(tx_contents['vin'][1]['txid'])

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

    dcrctl.shutdown()

if __name__ == '__main__':
    main()
