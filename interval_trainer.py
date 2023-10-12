import numpy as np
import tempfile
from copy import deepcopy
from music21 import converter, midi
from music21.note import Note
from music21.pitch import Pitch
from music21.interval import DiatonicInterval
from music21.analysis.enharmonics import EnharmonicSimplifier
from music21.stream import Stream, Measure
from music21.clef import TrebleClef, BassClef
from music21.meter import TimeSignature
from music21.style import Style
import PySimpleGUI as sg

appname = 'interval_trainer'
treble_clef = TrebleClef()
bass_clef = BassClef()
ts = TimeSignature('4/4')
ts.style.hideObjectOnPrint = True

intervals_list = [
    # 'P1',
    # 'd2',
    'm2',
    'M2',
    'A2',
    'd3',
    'm3',
    'M3',
    'A3',
    'd4',
    'P4',
    'A4',
    'd5',
    'P5',
    'A5',
    'd6',
    'm6',
    'M6',
    'A6',
    'd7',
    'm7',
    'M7',
    'A7',
    'd8',
    'P8',
    # 'A8',
]


def get_trial_random_interval_and_pitch(input_pitch):
    global last_8_pitches
    global last_8_intervals
    interval = np.random.choice(intervals_list)
    specifier = interval[0]
    generic = int(interval[1])
    if interval == 'P1':
        generic = 1
    elif np.random.random() > 0.5:
        generic = -generic
    interval = DiatonicInterval(specifier, generic)
    new_pitch = interval.transposePitch(input_pitch)
    if (
        (
            (new_pitch.accidental is not None)
            and (len(new_pitch.accidental.modifier) > 2)
        ) or (
            new_pitch < Pitch('G2')
        ) or (
            new_pitch > Pitch('E4')
        ) or (
            # Exclude pitches which are enharmonic with the current
            new_pitch.midi == input_pitch.midi
        ) or (
            (not window['-allow_double_accidentals-'])
            and (new_pitch.accidental is not None)
            and (len(new_pitch.accidental.modifier) == 2)
        ) or (
            new_pitch in last_8_pitches
        ) or (
            check_ratio_of_augmented_and_diminished_above_threshold()
            and (interval.specifier.name in ('AUGMENTED', 'DIMINISHED'))
        )
    ):
        return None, current_pitch
    return interval, new_pitch


augdim_threshold = 0.25
def check_ratio_of_augmented_and_diminished_above_threshold():
    global last_8_intervals
    sum_augdim = sum([1 for x in last_8_intervals if x.specifier.name in ('AUGMENTED', 'DIMINISHED')])
    return (sum_augdim / (len(last_8_intervals) if len(last_8_intervals) > 0 else 1)) > augdim_threshold


def get_new_random_interval_and_pitch(input_pitch, verbose=False):
    global last_8_pitches
    global last_8_intervals
    for i in range(9999):
        interval, new_pitch = get_trial_random_interval_and_pitch(input_pitch)
        if interval is not None:
            break
    last_8_pitches.append(new_pitch)
    if len(last_8_pitches) > 8:
        last_8_pitches = last_8_pitches[1:]
    last_8_intervals.append(interval)
    if len(last_8_intervals) > 8:
        last_8_intervals = last_8_intervals[1:]
    if verbose:
        print(interval.directedNiceName, new_pitch)
    return interval, new_pitch


def play_pitch(pitch):
    note_to_play = Note(pitch=pitch, type='half')
    music_stream.append(note_to_play)
    music_stream_player.play()
    for note in music_stream.notes:
        music_stream.remove(note)


def write_pitch_image(pitch):
    tempdir = tempfile.gettempdir()
    # NOTE: In principle should clean up these files, but they should be fairly small, and the writer overwrites them, so there shouldn't ever be more than one copy of each file
    pitch_no_accidental = deepcopy(pitch)
    pitch_no_accidental.accidental = None
    clef = treble_clef if pitch_no_accidental >= Pitch('C4') else bass_clef
    music_image_stream = Measure([ts, clef])
    music_image_stream.append(Note(pitch=current_pitch, type='whole'))
    png_output_path = music_image_stream.write(fmt='musicxml.png', fp=f'{tempdir}/{appname}_current_note')
    return str(png_output_path)


current_pitch = Pitch('A3')
last_8_pitches = [current_pitch]
last_8_intervals = []
current_pitch_png_path = write_pitch_image(current_pitch)

col1 = [
    [sg.Text('')],
    [sg.Text('Current pitch:'), sg.Text(current_pitch, key='-current_pitch-')],
    [sg.Text('')],
    [sg.Text('Target interval:'), sg.Text(key='-interval-', size=(30, 1))],
    [sg.Text('')],
    [sg.HSeparator()],
    [sg.Text('')],
    [sg.Button('Play current pitch 🔊 (p)')],
    [sg.Button('Reveal target pitch and give next interval (r)', key='-reveal-')],
    [sg.Button('Give me a different interval (i)')],
    [sg.Text('')],
    [sg.HSeparator()],
    [sg.Text('')],
    [sg.Text('')],
    [sg.Text('')],
    [sg.Text('')],
    [sg.Checkbox('Play the target pitch when revealing it', key='-play_pitch_when_revealing-', default=True)],
    [sg.Checkbox('Allow double accidentals', key='-allow_double_accidentals-', default=True)],
]

layout = [
    [
        sg.Column([
            [sg.Text(' '.join(appname.upper().replace('_', ' ')), justification='Center')],
            [sg.HSeparator()],
        ], expand_x=True, element_justification='center'),
    ],
    [
        sg.Column(col1, expand_y=True, vertical_alignment='center'),
        sg.VSeperator(),
        sg.Column([
            [sg.Text('')],
            [sg.Image(current_pitch_png_path, key='-note_image-')],
            [sg.Text('')],
            [sg.Quit('Quit (q)', key='-quit-')],
            [sg.Text('')],
        ], element_justification='center'),
    ]
]

sg.Text.fonts_installed_list()

window = sg.Window('Interval Trainer', layout, return_keyboard_events=True, font=("Monaco", 20), finalize=True)
music_stream = Stream()
music_stream_player = midi.realtime.StreamPlayer(music_stream)

interval, target_pitch = get_new_random_interval_and_pitch(current_pitch)
window['-interval-'].update(interval.directedNiceName)
last_8_intervals = [interval]


while True:
    event, values = window.read(timeout=1000)
    if event in ('Play current pitch 🔊 (p)', 'p'):
        play_pitch(current_pitch)
    if event in ('Give me a different interval (i)', 'i'):
        interval, target_pitch = get_new_random_interval_and_pitch(current_pitch)
        window['-interval-'].update(interval.directedNiceName)
    if event in ('-reveal-', 'r'):
        current_pitch = target_pitch
        window['-current_pitch-'].update(current_pitch.nameWithOctave.replace('-', 'b'))
        window['-interval-'].update('')
        if values['-play_pitch_when_revealing-'] == True:
            play_pitch(current_pitch)
        current_pitch_png_path = write_pitch_image(current_pitch)
        window['-note_image-'].update(current_pitch_png_path)
        interval, target_pitch = get_new_random_interval_and_pitch(current_pitch)
        window['-interval-'].update(interval.directedNiceName)
    if event in ('-quit-', 'q', sg.WIN_CLOSED):
        break

window.close()
