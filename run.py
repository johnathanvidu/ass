#! /usr/bin/python3.8
# ass - audio subtitles substituter 

import os
import sys
import glob
import json
import shutil
import logging
import subprocess


# logging
logger = logging.getLogger()
level = logging.DEBUG
logger.setLevel(level)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('- %(message)s | %(asctime)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Track:
	def __init__(self, uid, track_name, lang, default, matching):
		self.uid = uid
		self.track_name = track_name
		self.lang = lang
		self.default = default
		self.matching = matching

	def __str__(self):
		return f'track {self.track_name} id {self.uid} lang {self.lang} matching correct lang requested {self.matching}'


def scan_tracks(jmkv, audio_lang, subs_lang):
	result = {}
	tracks = jmkv['tracks']
	for track in tracks:
		type = track['type']
		properties = track['properties']
		matching = False
		if type == 'audio' and properties['language'] == audio_lang:
			matching = True
		if type == 'subtitles' and properties['language'] == subs_lang:
			matching = True

		if type not in result:
			result[type] = []

		uid = properties['number']
		track_name = properties['track_name'] if 'track_name' in properties else ''
		lang = properties['language']
		default = properties['default_track']
		result[type].append(Track(uid, track_name, lang, default, matching))
	return result


def set_default_audio(mkv, audio):
	logger.info('guessing correct audio track')
	correct_found = False
	edits = []
	for atrack in audio:
		logger.debug(atrack)
		if not atrack.matching:
			edits = edits + ['--edit', f'track:{int(atrack.uid)}', '--set', 'flag-default=0']
			continue

		track_name = atrack.track_name.lower()
		if 'commentary' in track_name:
			continue
		if 'song' in track_name or 'sing' in track_name:
			continue

		correct_found = True
		edits = edits + ['--edit', f'track:{int(atrack.uid)}', '--set', 'flag-default=1']
		logger.info(f'setting default audio track on {track_name} uid {atrack.uid}')

	if not correct_found:
		logger.warn('did not find suitable audio track, doing nothing...')
		return

	logger.info('mkvpropedit out')
	proc = subprocess.run(['mkvpropedit', mkv] + edits)
	logger.debug(' '.join(proc.args))


def set_default_subtitles(mkv, subtitles):
	logger.info('guessing correct subtitles track')
	correct_found = False
	edits = []
	for strack in subtitles:
		logger.debug(strack)
		if not strack.matching:
			edits = edits + ['--edit', f'track:{int(strack.uid)}', '--set', 'flag-default=0']
			continue

		track_name = strack.track_name.lower()
		if 'commentary' in track_name:
			edits = edits + ['--edit', f'track:{int(strack.uid)}', '--set', 'flag-default=0']
			continue
		if 'song' in track_name:
			edits = edits + ['--edit', f'track:{int(strack.uid)}', '--set', 'flag-default=0']
			continue
		if 'sing' in track_name:
			edits = edits + ['--edit', f'track:{int(strack.uid)}', '--set', 'flag-default=0']
			continue

		correct_found = True
		edits = edits + ['--edit', f'track:{int(strack.uid)}', '--set', 'flag-default=1']
		logger.info(f'setting default subtitles track on {track_name} uid {strack.uid}')

	if not correct_found:
		logger.warn('did not find suitable subtitles track, doing nothing...')
		return

	logger.info('mkvpropedit out')
	#proc = subprocess.run(['mkvpropedit', mkv, '--edit', f'track:{int(strack.uid)}', '--set', 'flag-default=1'])
	proc = subprocess.run(['mkvpropedit', mkv] + edits)
	logger.debug(' '.join(proc.args))


# main
logger.info('looking for mkvtoolnix...')
if shutil.which('mkvmerge') and shutil.which('mkvpropedit'):
	logger.info('mkvtoolnix found')
else:
	logger.error('mkvtoolnix must be installed')
	sys.exit(1)

logger.info(f'scanning current folder: {os.getcwd()}')
mkvs = glob.glob(f'{os.getcwd()}/*.mkv')
for mkv in mkvs:
	mkvmerge_proc = subprocess.run(['mkvmerge', '-J', mkv], stdout=subprocess.PIPE)
	jmkv = json.loads(mkvmerge_proc.stdout)
	tracks = scan_tracks(jmkv, 'jpn', 'eng')
	logger.info(f'editing {mkv}...')
	audio = tracks['audio']
	set_default_audio(mkv, audio)
	subs = tracks['subtitles']
	set_default_subtitles(mkv, subs)
logger.info('ass is done')
sys.exit(0)
