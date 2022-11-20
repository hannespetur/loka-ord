#!/usr/bin/python
"""
Exporter functionality

Exporting data from SQL database to files.
"""
import collections
import copy
import hashlib
import json
import os

from lokaord import logman
from lokaord.database import db
from lokaord.database.models import isl


def write_datafiles_from_db():
    logman.info('Writing datafiles from database ..')
    datafiles_dir_abs = os.path.abspath(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), 'database', 'data')
    )
    isl_ord_id_to_hash = {}
    hash_to_isl_ord_id = {}
    export_tasks = [
        {
            'name': 'nafnorð',
            'ordflokkur': isl.Ordflokkar.Nafnord,
            'root': datafiles_dir_abs,
            'dir': 'nafnord',
            'f_ord_to_dict': get_nafnord_from_db_to_ordered_dict,
            'has_samsett': True
        },
        {
            'name': 'lýsingarorð',
            'ordflokkur': isl.Ordflokkar.Lysingarord,
            'root': datafiles_dir_abs,
            'dir': 'lysingarord',
            'f_ord_to_dict': get_lysingarord_from_db_to_ordered_dict,
            'has_samsett': True
        },
        {
            'name': 'sagnorð',
            'ordflokkur': isl.Ordflokkar.Sagnord,
            'root': datafiles_dir_abs,
            'dir': 'sagnord',
            'f_ord_to_dict': get_sagnord_from_db_to_ordered_dict,
            'has_samsett': True
        },
        {
            'name': 'greinir',
            'ordflokkur': isl.Ordflokkar.Greinir,
            'root': datafiles_dir_abs,
            'dir': 'greinir',
            'f_ord_to_dict': get_greinir_from_db_to_ordered_dict,
            'has_samsett': False
        },
        {
            'name': 'töluorð frumtala',
            'ordflokkur': isl.Ordflokkar.Frumtala,
            'root': datafiles_dir_abs,
            'dir': os.path.join('toluord', 'frumtolur'),
            'f_ord_to_dict': get_frumtala_from_db_to_ordered_dict,
            'has_samsett': True
        },
        {
            'name': 'töluorð raðtala',
            'ordflokkur': isl.Ordflokkar.Radtala,
            'root': datafiles_dir_abs,
            'dir': os.path.join('toluord', 'radtolur'),
            'f_ord_to_dict': get_radtala_from_db_to_ordered_dict,
            'has_samsett': True
        },
        {
            'name': 'fornafn',
            'ordflokkur': isl.Ordflokkar.Fornafn,
            'root': datafiles_dir_abs,
            'dir': 'fornofn',
            'f_ord_to_dict': get_fornafn_from_db_to_ordered_dict,
            'has_samsett': True
        },
        {
            'name': 'forsetning',
            'ordflokkur': isl.Ordflokkar.Forsetning,
            'root': datafiles_dir_abs,
            'dir': os.path.join('smaord', 'forsetning'),
            'f_ord_to_dict': get_forsetning_from_db_to_ordered_dict,
            'has_samsett': False
        },
        {
            'name': 'atviksorð',
            'ordflokkur': isl.Ordflokkar.Atviksord,
            'root': datafiles_dir_abs,
            'dir': os.path.join('smaord', 'atviksord'),
            'f_ord_to_dict': get_atviksord_from_db_to_ordered_dict,
            'has_samsett': False
        },
        {
            'name': 'nafnháttarmerki',
            'ordflokkur': isl.Ordflokkar.Nafnhattarmerki,
            'root': datafiles_dir_abs,
            'dir': os.path.join('smaord', 'nafnhattarmerki'),
            'f_ord_to_dict': get_nafnhattarmerki_from_db_to_ordered_dict,
            'has_samsett': False
        },
    ]  # TODO: add rest of orðflokkar
    logman.info('We export core words first, then combined (samssett).')
    for task in export_tasks:
        do_export_task(task, hash_to_isl_ord_id, isl_ord_id_to_hash, do_samsett=False)
    logman.info('Now exporting combined words (samsett).')
    for task in export_tasks:
        do_export_task(task, hash_to_isl_ord_id, isl_ord_id_to_hash, do_samsett=True)
    #
    #
    # TODO: finish
    logman.info('TODO: finish implementing write_datafiles_from_db')


def do_export_task(task, hash_word_map, word_hash_map, do_samsett=False):
    if task['has_samsett'] is False and do_samsett is True:
        # nothing to do here
        return
    get_ord_from_db_to_ordered_dict = task['f_ord_to_dict']
    isl_ord_list = db.Session.query(isl.Ord).filter_by(
        Ordflokkur=task['ordflokkur'],
        Samsett=do_samsett
    ).order_by(isl.Ord.Ord, isl.Ord.Ord_id).all()
    for isl_ord in isl_ord_list:
        ord_data = None
        if do_samsett is True:
            ord_data = get_samsett_ord_from_db_to_ordered_dict(
                isl_ord, ord_id_hash_map=word_hash_map
            )
        elif do_samsett is False:
            ord_data = get_ord_from_db_to_ordered_dict(isl_ord)
        assert(ord_data is not None)
        ord_data_hash = hashify_ord_data(ord_data)
        # ensure unique ord_data_hash
        if ord_data_hash in hash_word_map:
            counter = 0
            while ord_data_hash_incr in hash_to_isl_ord_id:
                ord_data_hash_incr = '%s_%s' % (ord_data_hash, hex(counter)[2:])
                counter += 1
            ord_data_hash = ord_data_hash_incr
        hash_word_map[ord_data_hash] = isl_ord.Ord_id
        word_hash_map[str(isl_ord.Ord_id)] = ord_data_hash
        ord_data['hash'] = ord_data_hash
        ord_data_json_str = ord_data_to_fancy_json_str(ord_data)
        isl_ord_filename = '%s.json' % (ord_data['orð'], )
        if task['ordflokkur'] is isl.Ordflokkar.Nafnord:
            isl_ord_filename = '%s-%s%s.json' % (
                ord_data['orð'],
                ord_data['kyn'],
                '-ó' if ('ósjálfstætt' in ord_data and ord_data['ósjálfstætt'] is True) else ''
            )
        isl_ord_filepath = os.path.join(task['root'], task['dir'], isl_ord_filename)
        if task['ordflokkur'] is isl.Ordflokkar.Fornafn:
            subfolder_map = {
                'ábendingar': 'abendingar',
                'afturbeygt': 'afturbeygt',
                'eignar': 'eignar',
                'óákveðið': 'oakvedin',
                'persónu': 'personu',
                'spurnar': 'spurnar',
            }
            assert(ord_data['undirflokkur'] in subfolder_map)
            isl_ord_filepath = os.path.join(
                task['root'],
                task['dir'],
                subfolder_map[ord_data['undirflokkur']],
                isl_ord_filename
            )
        with open(isl_ord_filepath, mode='w', encoding='utf-8') as json_file:
            json_file.write(ord_data_json_str)
            logman.info('Wrote %s file "%s"' % (
                task['name'],
                os.path.join(task['dir'], isl_ord_filename),
            ))


def get_nafnord_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    assert(isl_ord.Ordflokkur is isl.Ordflokkar.Nafnord)
    data['flokkur'] = 'nafnorð'
    isl_nafnord_list = db.Session.query(isl.Nafnord).filter_by(
        fk_Ord_id=isl_ord.Ord_id
    )
    assert(len(isl_nafnord_list.all()) < 2)
    isl_nafnord = isl_nafnord_list.first()
    assert(isl_nafnord is not None)
    data['kyn'] = None
    if isl_nafnord.Kyn is isl.Kyn.Karlkyn:
        data['kyn'] = 'kk'
    elif isl_nafnord.Kyn is isl.Kyn.Kvenkyn:
        data['kyn'] = 'kvk'
    elif isl_nafnord.Kyn is isl.Kyn.Hvorugkyn:
        data['kyn'] = 'hk'
    assert(data['kyn'] is not None)
    if (
        isl_nafnord.fk_et_Fallbeyging_id is not None or
        isl_nafnord.fk_et_mgr_Fallbeyging_id
    ):
        data['et'] = collections.OrderedDict()
    if isl_nafnord.fk_et_Fallbeyging_id is not None:
        data['et']['ág'] = get_fallbeyging_list_from_db(
            isl_nafnord.fk_et_Fallbeyging_id
        )
    if isl_nafnord.fk_et_mgr_Fallbeyging_id is not None:
        data['et']['mg'] = get_fallbeyging_list_from_db(
            isl_nafnord.fk_et_mgr_Fallbeyging_id
        )
    if (
        isl_nafnord.fk_ft_Fallbeyging_id is not None or
        isl_nafnord.fk_ft_mgr_Fallbeyging_id is not None
    ):
        data['ft'] = collections.OrderedDict()
    if isl_nafnord.fk_ft_Fallbeyging_id is not None:
        data['ft']['ág'] = get_fallbeyging_list_from_db(
            isl_nafnord.fk_ft_Fallbeyging_id
        )
    if isl_nafnord.fk_ft_mgr_Fallbeyging_id is not None:
        data['ft']['mg'] = get_fallbeyging_list_from_db(
            isl_nafnord.fk_ft_mgr_Fallbeyging_id
        )
    if isl_ord.OsjalfstaedurOrdhluti is True:
        data['ósjálfstætt'] = True
    return data


def get_lysingarord_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'lýsingarorð'
    isl_lysingarord_list = db.Session.query(isl.Lysingarord).filter_by(
        fk_Ord_id=isl_ord.Ord_id
    )
    assert(len(isl_lysingarord_list.all()) < 2)
    isl_lysingarord = isl_lysingarord_list.first()
    assert(isl_lysingarord is not None)
    # setup data dict
    if (
        isl_lysingarord.fk_Frumstig_sb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['frumstig'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Frumstig_sb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_hk_Fallbeyging_id is not None
    ):
        data['frumstig']['sb'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Frumstig_sb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_et_hk_Fallbeyging_id is not None
    ):
        data['frumstig']['sb']['et'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Frumstig_sb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_sb_ft_hk_Fallbeyging_id is not None
    ):
        data['frumstig']['sb']['ft'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Frumstig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['frumstig']['vb'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Frumstig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_et_hk_Fallbeyging_id is not None
    ):
        data['frumstig']['vb']['et'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Frumstig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Frumstig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['frumstig']['vb']['ft'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Midstig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['miðstig'] = collections.OrderedDict()
        data['miðstig']['vb'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Midstig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_et_hk_Fallbeyging_id is not None
    ):
        data['miðstig']['vb']['et'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Midstig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Midstig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['miðstig']['vb']['ft'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_sb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['efstastig'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_sb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_hk_Fallbeyging_id is not None
    ):
        data['efstastig']['sb'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_sb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_et_hk_Fallbeyging_id is not None
    ):
        data['efstastig']['sb']['et'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_sb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_sb_ft_hk_Fallbeyging_id is not None
    ):
        data['efstastig']['sb']['ft'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_hk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['efstastig']['vb'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_vb_et_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_et_hk_Fallbeyging_id is not None
    ):
        data['efstastig']['vb']['et'] = collections.OrderedDict()
    if (
        isl_lysingarord.fk_Efstastig_vb_ft_kk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_kvk_Fallbeyging_id is not None or
        isl_lysingarord.fk_Efstastig_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['efstastig']['vb']['ft'] = collections.OrderedDict()
    # Frumstig, sterk beyging
    if isl_lysingarord.fk_Frumstig_sb_et_kk_Fallbeyging_id is not None:
        data['frumstig']['sb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_sb_et_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_sb_et_kvk_Fallbeyging_id is not None:
        data['frumstig']['sb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_sb_et_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_sb_et_hk_Fallbeyging_id is not None:
        data['frumstig']['sb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_sb_et_hk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_sb_ft_kk_Fallbeyging_id is not None:
        data['frumstig']['sb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_sb_ft_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_sb_ft_kvk_Fallbeyging_id is not None:
        data['frumstig']['sb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_sb_ft_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_sb_ft_hk_Fallbeyging_id is not None:
        data['frumstig']['sb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_sb_ft_hk_Fallbeyging_id
        )
    # Frumstig, veik beyging
    if isl_lysingarord.fk_Frumstig_vb_et_kk_Fallbeyging_id is not None:
        data['frumstig']['vb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_vb_et_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_vb_et_kvk_Fallbeyging_id is not None:
        data['frumstig']['vb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_vb_et_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_vb_et_hk_Fallbeyging_id is not None:
        data['frumstig']['vb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_vb_et_hk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_vb_ft_kk_Fallbeyging_id is not None:
        data['frumstig']['vb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_vb_ft_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_vb_ft_kvk_Fallbeyging_id is not None:
        data['frumstig']['vb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_vb_ft_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Frumstig_vb_ft_hk_Fallbeyging_id is not None:
        data['frumstig']['vb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Frumstig_vb_ft_hk_Fallbeyging_id
        )
    # Miðstig, veik beyging (miðstig hafa enga sterka beygingu)
    if isl_lysingarord.fk_Midstig_vb_et_kk_Fallbeyging_id is not None:
        data['miðstig']['vb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Midstig_vb_et_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Midstig_vb_et_kvk_Fallbeyging_id is not None:
        data['miðstig']['vb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Midstig_vb_et_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Midstig_vb_et_hk_Fallbeyging_id is not None:
        data['miðstig']['vb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Midstig_vb_et_hk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Midstig_vb_ft_kk_Fallbeyging_id is not None:
        data['miðstig']['vb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Midstig_vb_ft_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Midstig_vb_ft_kvk_Fallbeyging_id is not None:
        data['miðstig']['vb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Midstig_vb_ft_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Midstig_vb_ft_hk_Fallbeyging_id is not None:
        data['miðstig']['vb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Midstig_vb_ft_hk_Fallbeyging_id
        )
    # Efsta stig, sterk beyging
    if isl_lysingarord.fk_Efstastig_sb_et_kk_Fallbeyging_id is not None:
        data['efstastig']['sb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_sb_et_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_sb_et_kvk_Fallbeyging_id is not None:
        data['efstastig']['sb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_sb_et_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_sb_et_hk_Fallbeyging_id is not None:
        data['efstastig']['sb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_sb_et_hk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_sb_ft_kk_Fallbeyging_id is not None:
        data['efstastig']['sb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_sb_ft_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_sb_ft_kvk_Fallbeyging_id is not None:
        data['efstastig']['sb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_sb_ft_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_sb_ft_hk_Fallbeyging_id is not None:
        data['efstastig']['sb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_sb_ft_hk_Fallbeyging_id
        )
    # Efsta stig, veik beyging
    if isl_lysingarord.fk_Efstastig_vb_et_kk_Fallbeyging_id is not None:
        data['efstastig']['vb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_vb_et_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_vb_et_kvk_Fallbeyging_id is not None:
        data['efstastig']['vb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_vb_et_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_vb_et_hk_Fallbeyging_id is not None:
        data['efstastig']['vb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_vb_et_hk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_vb_ft_kk_Fallbeyging_id is not None:
        data['efstastig']['vb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_vb_ft_kk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_vb_ft_kvk_Fallbeyging_id is not None:
        data['efstastig']['vb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_vb_ft_kvk_Fallbeyging_id
        )
    if isl_lysingarord.fk_Efstastig_vb_ft_hk_Fallbeyging_id is not None:
        data['efstastig']['vb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_lysingarord.fk_Efstastig_vb_ft_hk_Fallbeyging_id
        )
    return data


def get_sagnord_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'sagnorð'
    isl_sagnord_list = db.Session.query(isl.Sagnord).filter_by(fk_Ord_id=isl_ord.Ord_id)
    assert(len(isl_sagnord_list.all()) < 2)
    isl_sagnord = isl_sagnord_list.first()
    assert(isl_sagnord is not None)
    # setup data dict
    if (
        isl_sagnord.Germynd_Nafnhattur is not None or
        isl_sagnord.Germynd_Sagnbot is not None or
        isl_sagnord.Germynd_Bodhattur_styfdur is not None or
        isl_sagnord.Germynd_Bodhattur_et is not None or
        isl_sagnord.Germynd_Bodhattur_ft is not None or
        isl_sagnord.fk_Germynd_personuleg_framsoguhattur is not None or
        isl_sagnord.fk_Germynd_personuleg_vidtengingarhattur is not None or
        isl_sagnord.Germynd_opersonuleg_frumlag is not None or
        isl_sagnord.fk_Germynd_opersonuleg_framsoguhattur is not None or
        isl_sagnord.fk_Germynd_opersonuleg_vidtengingarhattur is not None or
        isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
        isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_ft is not None or
        isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_et is not None or
        isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_ft is not None or
        isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
        isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None or
        isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None or
        isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
    ):
        data['germynd'] = collections.OrderedDict()
        # germynd nafnháttur
        if isl_sagnord.Germynd_Nafnhattur is not None:
            data['germynd']['nafnháttur'] = isl_sagnord.Germynd_Nafnhattur
        # germynd sagnbót
        if isl_sagnord.Germynd_Sagnbot is not None:
            data['germynd']['sagnbót'] = isl_sagnord.Germynd_Sagnbot
        if (
            isl_sagnord.Germynd_Bodhattur_styfdur is not None or
            isl_sagnord.Germynd_Bodhattur_et is not None or
            isl_sagnord.Germynd_Bodhattur_ft is not None
        ):
            data['germynd']['boðháttur'] = collections.OrderedDict()
        if (
            isl_sagnord.fk_Germynd_personuleg_framsoguhattur is not None or
            isl_sagnord.fk_Germynd_personuleg_vidtengingarhattur is not None
        ):
            data['germynd']['persónuleg'] = collections.OrderedDict()
        if (
            isl_sagnord.Germynd_opersonuleg_frumlag is not None or
            isl_sagnord.fk_Germynd_opersonuleg_framsoguhattur is not None or
            isl_sagnord.fk_Germynd_opersonuleg_vidtengingarhattur is not None
        ):
            data['germynd']['ópersónuleg'] = collections.OrderedDict()
        if (
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_ft is not None or
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_et is not None or
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_ft is not None or
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None or
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None or
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
        ):
            data['germynd']['spurnarmyndir'] = collections.OrderedDict()
            if (
                isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
                isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_ft is not None or
                isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_et is not None or
                isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_ft is not None
            ):
                data['germynd']['spurnarmyndir']['framsöguháttur'] = collections.OrderedDict()
                if (
                    isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
                    isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_ft is not None
                ):
                    data['germynd']['spurnarmyndir']['framsöguháttur']['nútíð'] = (
                        collections.OrderedDict()
                    )
                if (
                    isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_et is not None or
                    isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_ft is not None
                ):
                    data['germynd']['spurnarmyndir']['framsöguháttur']['þátíð'] = (
                        collections.OrderedDict()
                    )
            if (
                isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
                isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None or
                isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None or
                isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
            ):
                data['germynd']['spurnarmyndir']['viðtengingarháttur'] = collections.OrderedDict()
                if (
                    isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
                    isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None
                ):
                    data['germynd']['spurnarmyndir']['viðtengingarháttur']['nútíð'] = (
                        collections.OrderedDict()
                    )
                if (
                    isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None or
                    isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
                ):
                    data['germynd']['spurnarmyndir']['viðtengingarháttur']['þátíð'] = (
                        collections.OrderedDict()
                    )
    if (
        isl_sagnord.Midmynd_Nafnhattur is not None or
        isl_sagnord.Midmynd_Sagnbot is not None or
        isl_sagnord.Midmynd_Bodhattur_et is not None or
        isl_sagnord.Midmynd_Bodhattur_ft is not None or
        isl_sagnord.fk_Midmynd_personuleg_framsoguhattur is not None or
        isl_sagnord.fk_Midmynd_personuleg_vidtengingarhattur is not None or
        isl_sagnord.Midmynd_opersonuleg_frumlag is not None or
        isl_sagnord.fk_Midmynd_opersonuleg_framsoguhattur is not None or
        isl_sagnord.fk_Midmynd_opersonuleg_vidtengingarhattur is not None or
        isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
        # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_ft is not None or
        isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_et is not None or
        # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_ft is not None or
        isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
        # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None or
        isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None
        # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
    ):
        data['miðmynd'] = collections.OrderedDict()
        # miðmynd nafnháttur
        if isl_sagnord.Midmynd_Nafnhattur is not None:
            data['miðmynd']['nafnháttur'] = isl_sagnord.Midmynd_Nafnhattur
        # miðmynd sagnbót
        if isl_sagnord.Midmynd_Sagnbot is not None:
            data['miðmynd']['sagnbót'] = isl_sagnord.Midmynd_Sagnbot
        if (
            isl_sagnord.Midmynd_Bodhattur_et is not None or
            isl_sagnord.Midmynd_Bodhattur_ft is not None
        ):
            data['miðmynd']['boðháttur'] = collections.OrderedDict()
        if (
            isl_sagnord.fk_Midmynd_personuleg_framsoguhattur is not None or
            isl_sagnord.fk_Midmynd_personuleg_vidtengingarhattur is not None
        ):
            data['miðmynd']['persónuleg'] = collections.OrderedDict()
        if (
            isl_sagnord.Midmynd_opersonuleg_frumlag is not None or
            isl_sagnord.fk_Midmynd_opersonuleg_framsoguhattur is not None or
            isl_sagnord.fk_Midmynd_opersonuleg_vidtengingarhattur is not None
        ):
            data['miðmynd']['ópersónuleg'] = collections.OrderedDict()
        if (
            isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
            # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_ft is not None or
            isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_et is not None or
            # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_ft is not None or
            isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
            # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None or
            isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None
            # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
        ):
            data['miðmynd']['spurnarmyndir'] = collections.OrderedDict()
            if (
                isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_et is not None or
                # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_ft is not None or
                isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_et is not None
                # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_ft is not None
            ):
                data['miðmynd']['spurnarmyndir']['framsöguháttur'] = collections.OrderedDict()
                if (
                    isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_et is not None
                    # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_ft is not None
                ):
                    data['miðmynd']['spurnarmyndir']['framsöguháttur']['nútíð'] = (
                        collections.OrderedDict()
                    )
                if (
                    isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_et is not None
                    # isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_ft is not None
                ):
                    data['miðmynd']['spurnarmyndir']['framsöguháttur']['þátíð'] = (
                        collections.OrderedDict()
                    )
            if (
                isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None or
                # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None or
                isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None
                # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
            ):
                data['miðmynd']['spurnarmyndir']['viðtengingarháttur'] = collections.OrderedDict()
                if (
                    isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None
                    # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None
                ):
                    data['miðmynd']['spurnarmyndir']['viðtengingarháttur']['nútíð'] = (
                        collections.OrderedDict()
                    )
                if (
                    isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None
                    # isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None
                ):
                    data['miðmynd']['spurnarmyndir']['viðtengingarháttur']['þátíð'] = (
                        collections.OrderedDict()
                    )
    if (
        isl_sagnord.LysingarhatturNutidar is not None or
        isl_sagnord.fk_LysingarhatturThatidar_sb_et_kk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_sb_et_kvk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_sb_et_hk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kvk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_sb_ft_hk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_vb_et_kk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_vb_et_kvk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_vb_et_hk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kvk_id is not None or
        isl_sagnord.fk_LysingarhatturThatidar_vb_ft_hk_id is not None
    ):
        data['lýsingarháttur'] = collections.OrderedDict()
        # lýsingarháttur nútíðar
        if isl_sagnord.LysingarhatturNutidar is not None:
            data['lýsingarháttur']['nútíðar'] = isl_sagnord.LysingarhatturNutidar
        if (
            isl_sagnord.fk_LysingarhatturThatidar_sb_et_kk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_sb_et_kvk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_sb_et_hk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kvk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_sb_ft_hk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_vb_et_kk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_vb_et_kvk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_vb_et_hk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kvk_id is not None or
            isl_sagnord.fk_LysingarhatturThatidar_vb_ft_hk_id is not None
        ):
            data['lýsingarháttur']['þátíðar'] = collections.OrderedDict()
            if (
                isl_sagnord.fk_LysingarhatturThatidar_sb_et_kk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_sb_et_kvk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_sb_et_hk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kvk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_sb_ft_hk_id is not None
            ):
                data['lýsingarháttur']['þátíðar']['sb'] = collections.OrderedDict()
                if (
                    isl_sagnord.fk_LysingarhatturThatidar_sb_et_kk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_sb_et_kvk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_sb_et_hk_id is not None
                ):
                    data['lýsingarháttur']['þátíðar']['sb']['et'] = collections.OrderedDict()
                if (
                    isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kvk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_sb_ft_hk_id is not None
                ):
                    data['lýsingarháttur']['þátíðar']['sb']['ft'] = collections.OrderedDict()
            if (
                isl_sagnord.fk_LysingarhatturThatidar_vb_et_kk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_vb_et_kvk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_vb_et_hk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kvk_id is not None or
                isl_sagnord.fk_LysingarhatturThatidar_vb_ft_hk_id is not None
            ):
                data['lýsingarháttur']['þátíðar']['vb'] = collections.OrderedDict()
                if (
                    isl_sagnord.fk_LysingarhatturThatidar_vb_et_kk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_vb_et_kvk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_vb_et_hk_id is not None
                ):
                    data['lýsingarháttur']['þátíðar']['vb']['et'] = collections.OrderedDict()
                if (
                    isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kvk_id is not None or
                    isl_sagnord.fk_LysingarhatturThatidar_vb_ft_hk_id is not None
                ):
                    data['lýsingarháttur']['þátíðar']['vb']['ft'] = collections.OrderedDict()
    # germynd boðháttur
    if isl_sagnord.Germynd_Bodhattur_styfdur is not None:
        data['germynd']['boðháttur']['stýfður'] = isl_sagnord.Germynd_Bodhattur_styfdur
        data['germynd']['boðháttur']['et'] = isl_sagnord.Germynd_Bodhattur_et
        data['germynd']['boðháttur']['ft'] = isl_sagnord.Germynd_Bodhattur_ft
    # germynd persónuleg
    if isl_sagnord.fk_Germynd_personuleg_framsoguhattur is not None:
        data['germynd']['persónuleg']['framsöguháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Germynd_personuleg_framsoguhattur
        )
    if isl_sagnord.fk_Germynd_personuleg_vidtengingarhattur is not None:
        data['germynd']['persónuleg']['viðtengingarháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Germynd_personuleg_vidtengingarhattur
        )
    # germynd ópersónuleg
    if isl_sagnord.Germynd_opersonuleg_frumlag == isl.Fall.Tholfall:
        data['germynd']['ópersónuleg']['frumlag'] = 'þolfall'
    elif isl_sagnord.Germynd_opersonuleg_frumlag == isl.Fall.Thagufall:
        data['germynd']['ópersónuleg']['frumlag'] = 'þágufall'
    elif isl_sagnord.Germynd_opersonuleg_frumlag == isl.Fall.Eignarfall:
        data['germynd']['ópersónuleg']['frumlag'] = 'eignarfall'
    if isl_sagnord.fk_Germynd_opersonuleg_framsoguhattur is not None:
        data['germynd']['ópersónuleg']['framsöguháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Germynd_opersonuleg_framsoguhattur
        )
    if isl_sagnord.fk_Germynd_opersonuleg_vidtengingarhattur is not None:
        data['germynd']['ópersónuleg']['viðtengingarháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Germynd_opersonuleg_vidtengingarhattur
        )
    # germynd spurnarmyndir
    if isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_et is not None:
        data['germynd']['spurnarmyndir']['framsöguháttur']['nútíð']['et'] = (
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_et
        )
    if isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_ft is not None:
        data['germynd']['spurnarmyndir']['framsöguháttur']['nútíð']['ft'] = (
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_nutid_ft
        )
    if isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_et is not None:
        data['germynd']['spurnarmyndir']['framsöguháttur']['þátíð']['et'] = (
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_et
        )
    if isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_ft is not None:
        data['germynd']['spurnarmyndir']['framsöguháttur']['þátíð']['ft'] = (
            isl_sagnord.Germynd_spurnarmyndir_framsoguhattur_thatid_ft
        )
    #
    if isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None:
        data['germynd']['spurnarmyndir']['viðtengingarháttur']['nútíð']['et'] = (
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_et
        )
    if isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None:
        data['germynd']['spurnarmyndir']['viðtengingarháttur']['nútíð']['ft'] = (
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_nutid_ft
        )
    if isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None:
        data['germynd']['spurnarmyndir']['viðtengingarháttur']['þátíð']['et'] = (
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_et
        )
    if isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None:
        data['germynd']['spurnarmyndir']['viðtengingarháttur']['þátíð']['ft'] = (
            isl_sagnord.Germynd_spurnarmyndir_vidtengingarhattur_thatid_ft
        )
    # miðmynd boðháttur
    if isl_sagnord.Midmynd_Bodhattur_et is not None:
        data['miðmynd']['boðháttur']['et'] = isl_sagnord.Midmynd_Bodhattur_et
    if isl_sagnord.Midmynd_Bodhattur_ft is not None:
        data['miðmynd']['boðháttur']['ft'] = isl_sagnord.Midmynd_Bodhattur_ft
    # miðmynd persónuleg
    if isl_sagnord.fk_Midmynd_personuleg_framsoguhattur is not None:
        data['miðmynd']['persónuleg']['framsöguháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Midmynd_personuleg_framsoguhattur
        )
    if isl_sagnord.fk_Midmynd_personuleg_vidtengingarhattur is not None:
        data['miðmynd']['persónuleg']['viðtengingarháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Midmynd_personuleg_vidtengingarhattur
        )
    # miðmynd ópersónuleg
    if isl_sagnord.Midmynd_opersonuleg_frumlag == isl.Fall.Tholfall:
        data['miðmynd']['ópersónuleg']['frumlag'] = 'þolfall'
    elif isl_sagnord.Midmynd_opersonuleg_frumlag == isl.Fall.Thagufall:
        data['miðmynd']['ópersónuleg']['frumlag'] = 'þágufall'
    elif isl_sagnord.Midmynd_opersonuleg_frumlag == isl.Fall.Eignarfall:
        data['miðmynd']['ópersónuleg']['frumlag'] = 'eignarfall'
    if isl_sagnord.fk_Midmynd_opersonuleg_framsoguhattur is not None:
        data['miðmynd']['ópersónuleg']['framsöguháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Midmynd_opersonuleg_framsoguhattur
        )
    if isl_sagnord.fk_Midmynd_opersonuleg_vidtengingarhattur is not None:
        data['miðmynd']['ópersónuleg']['viðtengingarháttur'] = get_sagnbeyging_obj_from_db(
            isl_sagnord.fk_Midmynd_opersonuleg_vidtengingarhattur
        )
    # miðmynd spurnarmyndir
    if isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_et is not None:
        data['miðmynd']['spurnarmyndir']['framsöguháttur']['nútíð']['et'] = (
            isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_et
        )
    # if isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_ft is not None:
    #     data['miðmynd']['spurnarmyndir']['framsöguháttur']['nútíð']['ft'] = (
    #         isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_nutid_ft
    #     )
    if isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_et is not None:
        data['miðmynd']['spurnarmyndir']['framsöguháttur']['þátíð']['et'] = (
            isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_et
        )
    # if isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_ft is not None:
    #     data['miðmynd']['spurnarmyndir']['framsöguháttur']['þátíð']['ft'] = (
    #         isl_sagnord.Midmynd_spurnarmyndir_framsoguhattur_thatid_ft
    #     )
    #
    if isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_et is not None:
        data['miðmynd']['spurnarmyndir']['viðtengingarháttur']['nútíð']['et'] = (
            isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_et
        )
    # if isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_ft is not None:
    #     data['miðmynd']['spurnarmyndir']['viðtengingarháttur']['nútíð']['ft'] = (
    #         isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_nutid_ft
    #     )
    if isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_et is not None:
        data['miðmynd']['spurnarmyndir']['viðtengingarháttur']['þátíð']['et'] = (
            isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_et
        )
    # if isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_ft is not None:
    #     data['miðmynd']['spurnarmyndir']['viðtengingarháttur']['þátíð']['ft'] = (
    #         isl_sagnord.Midmynd_spurnarmyndir_vidtengingarhattur_thatid_ft
    #     )
    # lýsingarháttur þátíðar
    if isl_sagnord.fk_LysingarhatturThatidar_sb_et_kk_id is not None:
        data['lýsingarháttur']['þátíðar']['sb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_sb_et_kk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_sb_et_kvk_id is not None:
        data['lýsingarháttur']['þátíðar']['sb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_sb_et_kvk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_sb_et_hk_id is not None:
        data['lýsingarháttur']['þátíðar']['sb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_sb_et_hk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kk_id is not None:
        data['lýsingarháttur']['þátíðar']['sb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kvk_id is not None:
        data['lýsingarháttur']['þátíðar']['sb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_sb_ft_kvk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_sb_ft_hk_id is not None:
        data['lýsingarháttur']['þátíðar']['sb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_sb_ft_hk_id
        )
    #
    if isl_sagnord.fk_LysingarhatturThatidar_vb_et_kk_id is not None:
        data['lýsingarháttur']['þátíðar']['vb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_vb_et_kk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_vb_et_kvk_id is not None:
        data['lýsingarháttur']['þátíðar']['vb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_vb_et_kvk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_vb_et_hk_id is not None:
        data['lýsingarháttur']['þátíðar']['vb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_vb_et_hk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kk_id is not None:
        data['lýsingarháttur']['þátíðar']['vb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kvk_id is not None:
        data['lýsingarháttur']['þátíðar']['vb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_vb_ft_kvk_id
        )
    if isl_sagnord.fk_LysingarhatturThatidar_vb_ft_hk_id is not None:
        data['lýsingarháttur']['þátíðar']['vb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_sagnord.fk_LysingarhatturThatidar_vb_ft_hk_id
        )
    return data


def get_samsett_ord_from_db_to_ordered_dict(isl_ord, ord_id_hash_map=None):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = ordflokkur_to_str(isl_ord.Ordflokkur)
    if isl_ord.Ordflokkur is isl.Ordflokkar.Nafnord:
        data['kyn'] = None
    elif isl_ord.Ordflokkur is isl.Ordflokkar.Frumtala:
        isl_frumtala_query = db.Session.query(isl.Frumtala).filter_by(
            fk_Ord_id=isl_ord.Ord_id
        )
        assert(len(isl_frumtala_query.all()) < 2)
        isl_frumtala = isl_frumtala_query.first()
        assert(isl_frumtala is not None)
        if isl_frumtala.Gildi is not None:
            data['gildi'] = isl_frumtala.Gildi
    elif isl_ord.Ordflokkur is isl.Ordflokkar.Radtala:
        isl_radtala_query = db.Session.query(isl.Radtala).filter_by(
            fk_Ord_id=isl_ord.Ord_id
        )
        assert(len(isl_radtala_query.all()) < 2)
        isl_radtala = isl_radtala_query.first()
        assert(isl_radtala is not None)
        if isl_radtala.Gildi is not None:
            data['gildi'] = isl_radtala.Gildi
    elif isl_ord.Ordflokkur is isl.Ordflokkar.Fornafn:
        isl_fornafn_query = db.Session.query(isl.Fornafn).filter_by(
            fk_Ord_id=isl_ord.Ord_id
        )
        assert(len(isl_fornafn_query.all()) < 2)
        isl_fornafn = isl_fornafn_query.first()
        assert(isl_fornafn is not None)
        data['undirflokkur'] = undirflokkur_to_str(isl_fornafn.Undirflokkur)
        if isl_fornafn.Persona is not None:
            data['persóna'] = persona_to_str(isl_fornafn.Persona)
        if isl_fornafn.Kyn is not None:
            data['kyn'] = kyn_to_str(isl_fornafn.Kyn)
    data['samsett'] = []
    isl_samsett_ord_list = db.Session.query(isl.SamsettOrd).filter_by(
        fk_Ord_id=isl_ord.Ord_id
    )
    assert(len(isl_samsett_ord_list.all()) < 2)
    isl_samsett_ord = isl_samsett_ord_list.first()
    assert(isl_samsett_ord is not None)
    isl_ordhluti = db.Session.query(isl.SamsettOrdhlutar).filter_by(
        SamsettOrdhlutar_id=isl_samsett_ord.fk_FyrstiOrdHluti_id
    ).first()
    assert(isl_ordhluti is not None)
    ordhluti_ids = set()
    samsett_ord_framhluti = ''
    samsett_ord_beygist = True
    samsett_ord_last_ordhluti_ord = None
    samsett_ord_last_ordhluti_nafnord = None
    while isl_ordhluti is not None:
        samsett_ord_last_ordhluti_nafnord = None
        # below assertion is to detect and prevent circular samsett orð definition
        assert(isl_ordhluti.SamsettOrdhlutar_id not in ordhluti_ids)
        ordhluti_ids.add(isl_ordhluti.SamsettOrdhlutar_id)
        ordhluti_data = collections.OrderedDict()
        if isl_ordhluti.fk_NaestiOrdhluti_id is not None:
            assert(isl_ordhluti.Ordmynd is not None)
            assert(isl_ordhluti.Gerd is not None)
        if isl_ordhluti.Ordmynd is not None:
            assert(isl_ordhluti.Gerd is not None)
            samsetning_gerd = None
            if isl_ordhluti.Gerd is isl.Ordasamsetningar.Stofnsamsetning:
                samsetning_gerd = 'stofn'
            elif isl_ordhluti.Gerd is isl.Ordasamsetningar.Eignarfallssamsetning:
                samsetning_gerd = 'eignarfalls'
            elif isl_ordhluti.Gerd is isl.Ordasamsetningar.Bandstafssamsetning:
                samsetning_gerd = 'bandstafs'
            assert(samsetning_gerd is not None)
            ordhluti_data['mynd'] = isl_ordhluti.Ordmynd
            ordhluti_data['samsetning'] = samsetning_gerd
            samsett_ord_framhluti += ordhluti_data['mynd']
        ordhluti_ord = db.Session.query(isl.Ord).filter_by(Ord_id=isl_ordhluti.fk_Ord_id).first()
        assert(ordhluti_ord is not None)
        ordhluti_data['orð'] = ordhluti_ord.Ord
        ordhluti_flokkur = ordflokkur_to_str(ordhluti_ord.Ordflokkur)
        ordhluti_data['flokkur'] = ordhluti_flokkur
        ordhluti_nafnord = None
        if ordhluti_ord.Ordflokkur is isl.Ordflokkar.Nafnord:
            # for nafnorð we want to display kyn too
            ordhluti_nafnord_query = db.Session.query(isl.Nafnord).filter_by(
                fk_Ord_id=ordhluti_ord.Ord_id
            )
            assert(len(ordhluti_nafnord_query.all()) < 2)
            ordhluti_nafnord = ordhluti_nafnord_query.first()
            assert(ordhluti_nafnord is not None)
            ordhluti_kyn = kyn_to_str(ordhluti_nafnord.Kyn)
            ordhluti_data['kyn'] = ordhluti_kyn
            if ordhluti_ord.OsjalfstaedurOrdhluti is True:
                ordhluti_data['ósjálfstætt'] = True
        elif ordhluti_ord.Ordflokkur is isl.Ordflokkar.Fornafn:
            # for fornafn we want to display undirflokkur too
            ordhluti_fornafn_query = db.Session.query(isl.Fornafn).filter_by(
                fk_Ord_id=ordhluti_ord.Ord_id
            )
            assert(len(ordhluti_fornafn_query.all()) < 2)
            ordhluti_fornafn = ordhluti_fornafn_query.first()
            assert(ordhluti_fornafn is not None)
            ordhluti_fornafn_undirflokkur = undirflokkur_to_str(ordhluti_fornafn.Undirflokkur)
            ordhluti_data['undirflokkur'] = ordhluti_fornafn_undirflokkur
        ordhluti_data['hash'] = None
        if ord_id_hash_map is not None and str(ordhluti_ord.Ord_id) in ord_id_hash_map:
            ordhluti_data['hash'] = ord_id_hash_map[str(ordhluti_ord.Ord_id)]
        if isl_ordhluti.fk_NaestiOrdhluti_id is not None:
            isl_ordhluti = db.Session.query(isl.SamsettOrdhlutar).filter_by(
                SamsettOrdhlutar_id=isl_ordhluti.fk_NaestiOrdhluti_id
            ).first()
            assert(isl_ordhluti is not None)
        else:
            samsett_ord_last_ordhluti_ord = ordhluti_ord
            if isl_ordhluti.Ordmynd is not None:
                # ef síðasti orðhlutinn hefur fasta mynd þá er ljóst að samsetta orðið beygist ekki
                samsett_ord_beygist = False
            if isl_ord.Ordflokkur is isl.Ordflokkar.Nafnord:
                assert(ordhluti_nafnord is not None)
                samsett_ord_last_ordhluti_nafnord = ordhluti_nafnord
            isl_ordhluti = None
        data['samsett'].append(ordhluti_data)
    if isl_ord.Ordflokkur is isl.Ordflokkar.Nafnord:
        assert(samsett_ord_last_ordhluti_nafnord is not None)
        data['kyn'] = kyn_to_str(samsett_ord_last_ordhluti_nafnord.Kyn)
    if samsett_ord_beygist is True:
        samsett_ord_last_ordhluti_ord_data = None
        if samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Nafnord:
            samsett_ord_last_ordhluti_ord_data = get_nafnord_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        elif samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Lysingarord:
            samsett_ord_last_ordhluti_ord_data = get_lysingarord_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        elif samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Sagnord:
            samsett_ord_last_ordhluti_ord_data = get_sagnord_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        elif samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Greinir:
            samsett_ord_last_ordhluti_ord_data = get_greinir_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        elif samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Frumtala:
            samsett_ord_last_ordhluti_ord_data = get_frumtala_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        elif samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Radtala:
            samsett_ord_last_ordhluti_ord_data = get_radtala_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        elif samsett_ord_last_ordhluti_ord.Ordflokkur is isl.Ordflokkar.Fornafn:
            samsett_ord_last_ordhluti_ord_data = get_fornafn_from_db_to_ordered_dict(
                samsett_ord_last_ordhluti_ord
            )
        # TODO: add more orðflokkar here :/
        assert(samsett_ord_last_ordhluti_ord_data is not None)
        samsett_ord_data = add_framhluti_to_ord_data(
            samsett_ord_framhluti, samsett_ord_last_ordhluti_ord_data
        )
        for key in samsett_ord_data:
            data[key] = samsett_ord_data[key]
    else:
        if isl_ord.Ordflokkur is isl.Ordflokkar.Lysingarord:
            data['óbeygjanlegt'] = True
    return data


def get_fallbeyging_list_from_db(fallbeyging_id):
    fb = db.Session.query(isl.Fallbeyging).filter_by(
        Fallbeyging_id=fallbeyging_id
    ).first()
    assert(fb is not None)
    return [fb.Nefnifall, fb.Tholfall, fb.Thagufall, fb.Eignarfall]


def get_sagnbeyging_obj_from_db(sagnbeyging_id):
    data = collections.OrderedDict()
    sagnbeyging = db.Session.query(isl.Sagnbeyging).filter_by(
        Sagnbeyging_id=sagnbeyging_id
    ).first()
    assert(sagnbeyging is not None)
    if (
        sagnbeyging.FyrstaPersona_eintala_nutid is not None or
        sagnbeyging.OnnurPersona_eintala_nutid is not None or
        sagnbeyging.ThridjaPersona_eintala_nutid is not None or
        sagnbeyging.FyrstaPersona_fleirtala_nutid is not None or
        sagnbeyging.OnnurPersona_fleirtala_nutid is not None or
        sagnbeyging.ThridjaPersona_fleirtala_nutid is not None
    ):
        data['nútíð'] = collections.OrderedDict()
    if (
        sagnbeyging.FyrstaPersona_eintala_thatid is not None or
        sagnbeyging.OnnurPersona_eintala_thatid is not None or
        sagnbeyging.ThridjaPersona_eintala_thatid is not None or
        sagnbeyging.FyrstaPersona_fleirtala_thatid is not None or
        sagnbeyging.OnnurPersona_fleirtala_thatid is not None or
        sagnbeyging.ThridjaPersona_fleirtala_thatid is not None
    ):
        data['þátíð'] = collections.OrderedDict()
    if (
        sagnbeyging.FyrstaPersona_eintala_nutid is not None or
        sagnbeyging.OnnurPersona_eintala_nutid is not None or
        sagnbeyging.ThridjaPersona_eintala_nutid is not None
    ):
        data['nútíð']['et'] = [
            sagnbeyging.FyrstaPersona_eintala_nutid,
            sagnbeyging.OnnurPersona_eintala_nutid,
            sagnbeyging.ThridjaPersona_eintala_nutid
        ]
    if (
        sagnbeyging.FyrstaPersona_fleirtala_nutid is not None or
        sagnbeyging.OnnurPersona_fleirtala_nutid is not None or
        sagnbeyging.ThridjaPersona_fleirtala_nutid is not None
    ):
        data['nútíð']['ft'] = [
            sagnbeyging.FyrstaPersona_fleirtala_nutid,
            sagnbeyging.OnnurPersona_fleirtala_nutid,
            sagnbeyging.ThridjaPersona_fleirtala_nutid
        ]
    if (
        sagnbeyging.FyrstaPersona_eintala_thatid is not None or
        sagnbeyging.OnnurPersona_eintala_thatid is not None or
        sagnbeyging.ThridjaPersona_eintala_thatid is not None
    ):
        data['þátíð']['et'] = [
            sagnbeyging.FyrstaPersona_eintala_thatid,
            sagnbeyging.OnnurPersona_eintala_thatid,
            sagnbeyging.ThridjaPersona_eintala_thatid
        ]
    if (
        sagnbeyging.FyrstaPersona_fleirtala_thatid is not None or
        sagnbeyging.OnnurPersona_fleirtala_thatid is not None or
        sagnbeyging.ThridjaPersona_fleirtala_thatid is not None
    ):
        data['þátíð']['ft'] = [
            sagnbeyging.FyrstaPersona_fleirtala_thatid,
            sagnbeyging.OnnurPersona_fleirtala_thatid,
            sagnbeyging.ThridjaPersona_fleirtala_thatid
        ]
    return data


def get_greinir_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'greinir'
    isl_greinir = db.Session.query(isl.Greinir).filter_by(fk_Ord_id=isl_ord.Ord_id).first()
    assert(isl_greinir is not None)
    if (
        isl_greinir.fk_et_kk_Fallbeyging_id is not None or
        isl_greinir.fk_et_kvk_Fallbeyging_id is not None or
        isl_greinir.fk_et_hk_Fallbeyging_id is not None
    ):
        data['et'] = collections.OrderedDict()
    if (
        isl_greinir.fk_ft_kk_Fallbeyging_id is not None or
        isl_greinir.fk_ft_kvk_Fallbeyging_id is not None or
        isl_greinir.fk_ft_hk_Fallbeyging_id is not None
    ):
        data['ft'] = collections.OrderedDict()
    # et
    if isl_greinir.fk_et_kk_Fallbeyging_id is not None:
        data['et']['kk'] = get_fallbeyging_list_from_db(isl_greinir.fk_et_kk_Fallbeyging_id)
    if isl_greinir.fk_et_kvk_Fallbeyging_id is not None:
        data['et']['kvk'] = get_fallbeyging_list_from_db(isl_greinir.fk_et_kvk_Fallbeyging_id)
    if isl_greinir.fk_et_hk_Fallbeyging_id is not None:
        data['et']['hk'] = get_fallbeyging_list_from_db(isl_greinir.fk_et_hk_Fallbeyging_id)
    # ft
    if isl_greinir.fk_ft_kk_Fallbeyging_id is not None:
        data['ft']['kk'] = get_fallbeyging_list_from_db(isl_greinir.fk_ft_kk_Fallbeyging_id)
    if isl_greinir.fk_ft_kvk_Fallbeyging_id is not None:
        data['ft']['kvk'] = get_fallbeyging_list_from_db(isl_greinir.fk_ft_kvk_Fallbeyging_id)
    if isl_greinir.fk_ft_hk_Fallbeyging_id is not None:
        data['ft']['hk'] = get_fallbeyging_list_from_db(isl_greinir.fk_ft_hk_Fallbeyging_id)
    return data


def get_frumtala_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'frumtala'
    isl_frumtala_query = db.Session.query(isl.Frumtala).filter_by(fk_Ord_id=isl_ord.Ord_id)
    assert(len(isl_frumtala_query.all()) < 2)
    isl_frumtala = isl_frumtala_query.first()
    assert(isl_frumtala is not None)
    if isl_frumtala.Gildi is not None:
        data['gildi'] = isl_frumtala.Gildi
    if (
        isl_frumtala.fk_et_kk_Fallbeyging_id is not None or
        isl_frumtala.fk_et_kvk_Fallbeyging_id is not None or
        isl_frumtala.fk_et_hk_Fallbeyging_id is not None
    ):
        data['et'] = collections.OrderedDict()
    if (
        isl_frumtala.fk_ft_kk_Fallbeyging_id is not None or
        isl_frumtala.fk_ft_kvk_Fallbeyging_id is not None or
        isl_frumtala.fk_ft_hk_Fallbeyging_id is not None
    ):
        data['ft'] = collections.OrderedDict()
    # et
    if isl_frumtala.fk_et_kk_Fallbeyging_id is not None:
        data['et']['kk'] = get_fallbeyging_list_from_db(isl_frumtala.fk_et_kk_Fallbeyging_id)
    if isl_frumtala.fk_et_kvk_Fallbeyging_id is not None:
        data['et']['kvk'] = get_fallbeyging_list_from_db(isl_frumtala.fk_et_kvk_Fallbeyging_id)
    if isl_frumtala.fk_et_hk_Fallbeyging_id is not None:
        data['et']['hk'] = get_fallbeyging_list_from_db(isl_frumtala.fk_et_hk_Fallbeyging_id)
    # ft
    if isl_frumtala.fk_ft_kk_Fallbeyging_id is not None:
        data['ft']['kk'] = get_fallbeyging_list_from_db(isl_frumtala.fk_ft_kk_Fallbeyging_id)
    if isl_frumtala.fk_ft_kvk_Fallbeyging_id is not None:
        data['ft']['kvk'] = get_fallbeyging_list_from_db(isl_frumtala.fk_ft_kvk_Fallbeyging_id)
    if isl_frumtala.fk_ft_hk_Fallbeyging_id is not None:
        data['ft']['hk'] = get_fallbeyging_list_from_db(isl_frumtala.fk_ft_hk_Fallbeyging_id)
    if 'et' not in data and 'ft' not in data:
        data['óbeygjanlegt'] = True
    return data


def get_radtala_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'raðtala'
    isl_radtala_query = db.Session.query(isl.Radtala).filter_by(fk_Ord_id=isl_ord.Ord_id)
    assert(len(isl_radtala_query.all()) < 2)
    isl_radtala = isl_radtala_query.first()
    assert(isl_radtala is not None)
    if isl_radtala.Gildi is not None:
        data['gildi'] = isl_radtala.Gildi
    if (
        isl_radtala.fk_sb_et_kk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_et_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_et_hk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_ft_kk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_ft_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_ft_hk_Fallbeyging_id is not None
    ):
        data['sb'] = collections.OrderedDict()
    if (
        isl_radtala.fk_sb_et_kk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_et_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_et_hk_Fallbeyging_id is not None
    ):
        data['sb']['et'] = collections.OrderedDict()
    if (
        isl_radtala.fk_sb_ft_kk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_ft_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_sb_ft_hk_Fallbeyging_id is not None
    ):
        data['sb']['ft'] = collections.OrderedDict()
    if (
        isl_radtala.fk_vb_et_kk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_et_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_et_hk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_ft_kk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_ft_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['vb'] = collections.OrderedDict()
    if (
        isl_radtala.fk_vb_et_kk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_et_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_et_hk_Fallbeyging_id is not None
    ):
        data['vb']['et'] = collections.OrderedDict()
    if (
        isl_radtala.fk_vb_ft_kk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_ft_kvk_Fallbeyging_id is not None or
        isl_radtala.fk_vb_ft_hk_Fallbeyging_id is not None
    ):
        data['vb']['ft'] = collections.OrderedDict()
    # sb et
    if isl_radtala.fk_sb_et_kk_Fallbeyging_id is not None:
        data['sb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_sb_et_kk_Fallbeyging_id
        )
    if isl_radtala.fk_sb_et_kvk_Fallbeyging_id is not None:
        data['sb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_sb_et_kvk_Fallbeyging_id
        )
    if isl_radtala.fk_sb_et_hk_Fallbeyging_id is not None:
        data['sb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_sb_et_hk_Fallbeyging_id
        )
    # sb ft
    if isl_radtala.fk_sb_ft_kk_Fallbeyging_id is not None:
        data['sb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_sb_ft_kk_Fallbeyging_id
        )
    if isl_radtala.fk_sb_ft_kvk_Fallbeyging_id is not None:
        data['sb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_sb_ft_kvk_Fallbeyging_id
        )
    if isl_radtala.fk_sb_ft_hk_Fallbeyging_id is not None:
        data['sb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_sb_ft_hk_Fallbeyging_id
        )
    # vb et
    if isl_radtala.fk_vb_et_kk_Fallbeyging_id is not None:
        data['vb']['et']['kk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_vb_et_kk_Fallbeyging_id
        )
    if isl_radtala.fk_vb_et_kvk_Fallbeyging_id is not None:
        data['vb']['et']['kvk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_vb_et_kvk_Fallbeyging_id
        )
    if isl_radtala.fk_vb_et_hk_Fallbeyging_id is not None:
        data['vb']['et']['hk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_vb_et_hk_Fallbeyging_id
        )
    # vb ft
    if isl_radtala.fk_vb_ft_kk_Fallbeyging_id is not None:
        data['vb']['ft']['kk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_vb_ft_kk_Fallbeyging_id
        )
    if isl_radtala.fk_vb_ft_kvk_Fallbeyging_id is not None:
        data['vb']['ft']['kvk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_vb_ft_kvk_Fallbeyging_id
        )
    if isl_radtala.fk_vb_ft_hk_Fallbeyging_id is not None:
        data['vb']['ft']['hk'] = get_fallbeyging_list_from_db(
            isl_radtala.fk_vb_ft_hk_Fallbeyging_id
        )
    return data


def get_fornafn_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'fornafn'
    isl_fornafn_query = db.Session.query(isl.Fornafn).filter_by(fk_Ord_id=isl_ord.Ord_id)
    assert(len(isl_fornafn_query.all()) < 2)
    isl_fornafn = isl_fornafn_query.first()
    try:
        assert(isl_fornafn is not None)
    except:
        import pdb; pdb.set_trace()
    data['undirflokkur'] = undirflokkur_to_str(isl_fornafn.Undirflokkur)
    if isl_fornafn.Persona is not None:
        data['persóna'] = persona_to_str(isl_fornafn.Persona)
    if isl_fornafn.Kyn is not None:
        data['kyn'] = kyn_to_str(isl_fornafn.Kyn)
    # et
    if isl_fornafn.fk_et_Fallbeyging_id is not None:
        data['et'] = get_fallbeyging_list_from_db(isl_fornafn.fk_et_Fallbeyging_id)
        assert(  # eintala fallbeyging should not be set for both genderless and gendered
            isl_fornafn.fk_et_kk_Fallbeyging_id is None and
            isl_fornafn.fk_et_kvk_Fallbeyging_id is None and
            isl_fornafn.fk_et_hk_Fallbeyging_id is None
        )
    elif (
        isl_fornafn.fk_et_kk_Fallbeyging_id is not None or
        isl_fornafn.fk_et_kvk_Fallbeyging_id is not None or
        isl_fornafn.fk_et_hk_Fallbeyging_id is not None
    ):
        data['et'] = collections.OrderedDict()
    # ft
    if isl_fornafn.fk_ft_Fallbeyging_id is not None:
        data['ft'] = get_fallbeyging_list_from_db(isl_fornafn.fk_ft_Fallbeyging_id)
        assert(  # eintala fallbeyging should not be set for both genderless and gendered
            isl_fornafn.fk_ft_kk_Fallbeyging_id is None and
            isl_fornafn.fk_ft_kvk_Fallbeyging_id is None and
            isl_fornafn.fk_ft_hk_Fallbeyging_id is None
        )
    elif (
        isl_fornafn.fk_ft_kk_Fallbeyging_id is not None or
        isl_fornafn.fk_ft_kvk_Fallbeyging_id is not None or
        isl_fornafn.fk_ft_hk_Fallbeyging_id is not None
    ):
        data['ft'] = collections.OrderedDict()
    # et
    if isl_fornafn.fk_et_kk_Fallbeyging_id is not None:
        data['et']['kk'] = get_fallbeyging_list_from_db(isl_fornafn.fk_et_kk_Fallbeyging_id)
    if isl_fornafn.fk_et_kvk_Fallbeyging_id is not None:
        data['et']['kvk'] = get_fallbeyging_list_from_db(isl_fornafn.fk_et_kvk_Fallbeyging_id)
    if isl_fornafn.fk_et_hk_Fallbeyging_id is not None:
        data['et']['hk'] = get_fallbeyging_list_from_db(isl_fornafn.fk_et_hk_Fallbeyging_id)
    # ft
    if isl_fornafn.fk_ft_kk_Fallbeyging_id is not None:
        data['ft']['kk'] = get_fallbeyging_list_from_db(isl_fornafn.fk_ft_kk_Fallbeyging_id)
    if isl_fornafn.fk_ft_kvk_Fallbeyging_id is not None:
        data['ft']['kvk'] = get_fallbeyging_list_from_db(isl_fornafn.fk_ft_kvk_Fallbeyging_id)
    if isl_fornafn.fk_ft_hk_Fallbeyging_id is not None:
        data['ft']['hk'] = get_fallbeyging_list_from_db(isl_fornafn.fk_ft_hk_Fallbeyging_id)
    return data


class MyJSONEncoder(json.JSONEncoder):
    '''
    json encoder for doing a little bit of custom json string indentation

    this extended class is a complete hack, I am a complete hack, but it f*cking works and I'm
    running with it
    '''
    def iterencode(self, o, _one_shot=False):
        list_lvl = 0
        keys_to_differently_encode = [
            'ág', 'mg', 'kk', 'kvk', 'hk', 'et', 'ft', 'stýrir'
        ]
        state = 0
        for s in super(MyJSONEncoder, self).iterencode(o, _one_shot=_one_shot):
            if state == 0:
                if s.startswith('"') and s.endswith('"') and s[1:-1] in keys_to_differently_encode:
                    state += 1
            elif state == 1:
                if s == ': ':
                    state += 1
                else:
                    state = 0
            elif state == 2:
                if s.startswith('['):
                    list_lvl += 1
                    s = ''.join([x.strip() for x in s.split('\n')])
                elif 0 < list_lvl:
                    s = ''.join([x.strip() for x in s.split('\n')])
                    if s and s.startswith(','):
                        s = ', ' + s[1:]
                if s.endswith(']'):
                    list_lvl -= 1
                    state = 0
                if s.endswith('}'):
                    state = 0
            yield s


def ord_data_to_fancy_json_str(ord_data):
    return json.dumps(
        ord_data, indent='\t', ensure_ascii=False, separators=(',', ': '), cls=MyJSONEncoder
    )


def hashify_ord_data(ord_data):
    '''
    create hash for orð data (which could be used for identification maybe?)
    '''
    if 'hash' in ord_data:
        ord_data = copy.deepcopy(ord_data)
        del ord_data['hash']
    return hashlib.sha256(
        json.dumps(
            ord_data, separators=(',', ':'), ensure_ascii=False, sort_keys=True
        ).encode('utf-8')
    ).hexdigest()


def ordflokkur_to_str(ordflokkur):
    if ordflokkur is isl.Ordflokkar.Nafnord:
        return 'nafnorð'
    elif ordflokkur is isl.Ordflokkar.Lysingarord:
        return 'lýsingarorð'
    elif ordflokkur is isl.Ordflokkar.Greinir:
        return 'greinir'
    elif ordflokkur is isl.Ordflokkar.Frumtala:
        return 'frumtala'
    elif ordflokkur is isl.Ordflokkar.Radtala:
        return 'raðtala'
    elif ordflokkur is isl.Ordflokkar.Fornafn:
        return 'fornafn'
    elif ordflokkur is isl.Ordflokkar.Sagnord:
        return 'sagnorð'
    elif ordflokkur is isl.Ordflokkar.Forsetning:
        return 'forsetning'
    elif ordflokkur is isl.Ordflokkar.Atviksord:
        return 'atviksorð'
    elif ordflokkur is isl.Ordflokkar.Nafnhattarmerki:
        return 'nafnháttarmerki'
    elif ordflokkur is isl.Ordflokkar.Samtenging:
        return 'samtenging'
    elif ordflokkur is isl.Ordflokkar.Upphropun:
        return 'upphrópun'
    raise Exception('Unknown orðflokkur.')


def kyn_to_str(kyn):
    if kyn is isl.Kyn.Karlkyn:
        return 'kk'
    elif kyn is isl.Kyn.Kvenkyn:
        return 'kvk'
    elif kyn is isl.Kyn.Hvorugkyn:
        return 'hk'
    raise Exception('Unknown kyn.')


def add_framhluti_to_ord_data(framhluti, ord_data):
    '''
    helper function for constructing beygingarmyndir data for samsett orð
    '''
    dictorinos = (dict, collections.OrderedDict)
    ignore_keys = set(['orð', 'flokkur', 'undirflokkur', 'kyn', 'gildi', 'hash', 'ósjálfstætt'])
    dont_change_keys = set(['frumlag'])
    new_ord_data = None
    if type(ord_data) is dict:
        new_ord_data = {}
    if type(ord_data) is collections.OrderedDict:
        new_ord_data = collections.OrderedDict()
    if type(ord_data) in dictorinos:
        for key in ord_data:
            if key in ignore_keys:
                continue
            elif key in dont_change_keys:
                new_ord_data[key] = ord_data[key]
            else:
                new_ord_data[key] = add_framhluti_to_ord_data(framhluti, ord_data[key])
    if type(ord_data) is list:
        new_ord_data = []
        for element in ord_data:
            new_ord_data.append(add_framhluti_to_ord_data(framhluti, element))
    if type(ord_data) is str:
        new_ord_data = '%s%s' % (framhluti, ord_data)
    if type(ord_data) is bool:
        new_ord_data = ord_data
    if type(ord_data) is int:
        new_ord_data = ord_data
    if type(ord_data) is None:
        new_ord_data = ord_data
    return new_ord_data


def undirflokkur_to_str(undirflokkur):
    if undirflokkur is isl.Fornafnaflokkar.Abendingarfornafn:
        return 'ábendingar'
    elif undirflokkur is isl.Fornafnaflokkar.AfturbeygtFornafn:
        return 'afturbeygt'
    elif undirflokkur is isl.Fornafnaflokkar.Eignarfornafn:
        return 'eignar'
    elif undirflokkur is isl.Fornafnaflokkar.OakvedidFornafn:
        return 'óákveðið'
    elif undirflokkur is isl.Fornafnaflokkar.Personufornafn:
        return 'persónu'
    elif undirflokkur is isl.Fornafnaflokkar.Spurnarfornafn:
        return 'spurnar'
    raise Exception('Unknown undirorðflokkur.')


def persona_to_str(persona):
    if persona is isl.Persona.Fyrsta:
        return 'fyrsta'
    elif persona is isl.Persona.Onnur:
        return 'önnur'
    elif persona is isl.Persona.Thridja:
        return 'þriðja'
    raise Exception('Unknown persóna.')


def get_forsetning_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'smáorð'
    data['undirflokkur'] = 'forsetning'
    isl_forsetning_query = db.Session.query(isl.Forsetning).filter_by(fk_Ord_id=isl_ord.Ord_id)
    assert(len(isl_forsetning_query.all()) < 2)
    isl_forsetning = isl_forsetning_query.first()
    assert(isl_forsetning is not None)
    if (
        isl_forsetning.StyrirTholfalli is True or
        isl_forsetning.StyrirThagufalli is True or
        isl_forsetning.StyrirEignarfalli is True
    ):
        data['stýrir'] = []
        if isl_forsetning.StyrirTholfalli is True:
            data['stýrir'].append('þolfall')
        if isl_forsetning.StyrirThagufalli is True:
            data['stýrir'].append('þágufall')
        if isl_forsetning.StyrirEignarfalli is True:
            data['stýrir'].append('eignarfall')
    return data


def get_atviksord_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'smáorð'
    data['undirflokkur'] = 'atviksorð'
    isl_atviksord_query = db.Session.query(isl.Atviksord).filter_by(fk_Ord_id=isl_ord.Ord_id)
    assert(len(isl_atviksord_query.all()) < 2)
    isl_atviksord = isl_atviksord_query.first()
    if isl_atviksord is not None:
        assert(isl_atviksord.Midstig is not None and isl_atviksord.Efstastig is not None)
        data['miðstig'] = isl_atviksord.Midstig
        data['efstastig'] = isl_atviksord.Efstastig
    return data


def get_nafnhattarmerki_from_db_to_ordered_dict(isl_ord):
    data = collections.OrderedDict()
    data['orð'] = isl_ord.Ord
    data['flokkur'] = 'smáorð'
    data['undirflokkur'] = 'nafnháttarmerki'
    return data
