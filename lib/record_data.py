from config.config import *
import pyaudio
import wave
import time
from time import sleep
import scipy.io.wavfile
import audioop
import math
import numpy as np
from scipy.fftpack import fft
from scipy.fftpack import fftfreq
from scipy.signal import blackmanharris
from lib.machinelearning import get_loudest_freq
import os
import msvcrt
from queue import *
import threading
import traceback
import sys

# Countdown from seconds to 0
def countdown( seconds ):
	for i in range( -seconds, 0 ):
		print("recording in... " + str(abs(i)), end="\r")
		sleep( 1 )
		if( record_controls() == False ):
			return False;
	print("                          ", end="\r")
	return True

def record_controls( recordQueue=None ):
	ESCAPEKEY = b'\x1b'
	SPACEBAR = b' '
	
	if( msvcrt.kbhit() ):
		character = msvcrt.getch()
		if( character == SPACEBAR ):
			print( "Recording paused!" )

			# Pause the recording by looping until we get a new keypress
			while( True ):
				
				## If the audio queue exists - make sure to clear it continuously
				if( recordQueue != None ):
					recordQueue.queue.clear()
			
				if( msvcrt.kbhit() ):
					character = msvcrt.getch()
					if( character == SPACEBAR ):
						print( "Recording resumed!" )
						return True
					elif( character == ESCAPEKEY ):
						print( "Recording stopped" )
						return False
		elif( character == ESCAPEKEY ):
			print( "Recording stopped" )
			return False
			
		print( character )
	return True	
	
def record_sound():	
	print( "-------------------------" )
	print( "Let's record some sounds!")
	print( "This script is going to listen to your microphone input" )
	print( "And record tiny audio files to be used for learning later" )
	print( "-------------------------" )

	directory = input("Whats the name of the sound are you recording? ")
	if not os.path.exists(RECORDINGS_FOLDER + "/" + directory):
		os.makedirs(RECORDINGS_FOLDER + "/"  + directory)

	threshold = input("What loudness threshold do you need? " )
	if( threshold == "" ):
		threshold = 0
	else:
		threshold = int(threshold)
	frequency_threshold = input("What frequency threshold do you need? " )
	if( frequency_threshold == "" ):
		frequency_threshold = 0
	else:
		frequency_threshold = int( frequency_threshold )
		
	print("")
	print("You can pause/resume the recording session using the [SPACE] key, and stop the recording using the [ESC] key" )

	WAVE_OUTPUT_FILENAME = RECORDINGS_FOLDER + "/" + directory + "/" + str(int(time.time() ) ) + "file";
	WAVE_OUTPUT_FILE_EXTENSION = ".wav";

	if( countdown( 5 ) == False ):
		return;
		
	non_blocking_record(threshold, frequency_threshold, WAVE_OUTPUT_FILENAME, WAVE_OUTPUT_FILE_EXTENSION)
	
# Consumes the recordings in a sliding window fashion - Always combining the two latest chunks together	
def record_consumer(threshold, frequency_threshold, WAVE_OUTPUT_FILENAME, WAVE_OUTPUT_FILE_EXTENSION, audio, stream):
	global recordQueue

	files_recorded = 0
	j = 0
	audioFrames = []
	try:
		while( True ):
			audioFrames.append( recordQueue.get() )		
			if( len( audioFrames ) >= 2 ):
				j+=1
				if( len( audioFrames ) > 2 ):
					audioFrames = audioFrames[1:]
					
				intensity = [
					audioop.maxpp( audioFrames[0], 4 ) / 32767,
					audioop.maxpp( audioFrames[1], 4 ) / 32767
				]
				highestintensity = np.amax( intensity )
				
				byteString = b''.join(audioFrames)
				fftData = np.frombuffer( byteString, dtype=np.int16 )
				frequency = get_loudest_freq( fftData, RECORD_SECONDS )
				
				fileid = "%0.2f" % ((j) * RECORD_SECONDS )
			
				if( record_controls( recordQueue ) == False ):
					stream.stop_stream()
					break;
					 
				if( frequency > frequency_threshold and highestintensity > threshold ):
					files_recorded += 1
					print( "Files recorded: %0d - Intensity: %0d - Freq: %0d - Saving %s" % ( files_recorded, highestintensity, frequency, fileid ) )
					waveFile = wave.open(WAVE_OUTPUT_FILENAME + fileid + WAVE_OUTPUT_FILE_EXTENSION, 'wb')
					waveFile.setnchannels(CHANNELS)
					waveFile.setsampwidth(audio.get_sample_size(FORMAT))
					waveFile.setframerate(RATE)
					waveFile.writeframes(byteString)
					waveFile.close()
					waveFile.aliaaa()
				else:
					print( "Files recorded: %0d - Intensity: %0d - Freq: %0d" % ( files_recorded, highestintensity, frequency ) )
	except Exception as e:
		print( "----------- ERROR DURING RECORDING -------------- " )
		exc_type, exc_value, exc_tb = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_tb)
		stream.stop_stream()

def multithreaded_record( in_data, frame_count, time_info, status ):
	global recordQueue
	recordQueue.put( in_data )
	
	return in_data, pyaudio.paContinue
				
# Records a non blocking audio stream and saves the chunks onto a queue
# The queue will be used as a sliding window over the audio, where two chunks are combined into one audio file
def non_blocking_record(threshold, frequency_threshold, WAVE_OUTPUT_FILENAME, WAVE_OUTPUT_FILE_EXTENSION):
	global recordQueue
	recordQueue = Queue(maxsize=0)

	audio = pyaudio.PyAudio()
	stream = audio.open(format=FORMAT, channels=CHANNELS,
		rate=RATE, input=True,
		input_device_index=INPUT_DEVICE_INDEX,
		frames_per_buffer=CHUNK,
		stream_callback=multithreaded_record)
		
	consumer = threading.Thread(name='consumer', target=record_consumer, args=(threshold, frequency_threshold, WAVE_OUTPUT_FILENAME, WAVE_OUTPUT_FILE_EXTENSION, audio, stream))
	consumer.setDaemon( True )
	consumer.start()
	stream.start_stream()

	# wait for stream to finish (5)
	while stream.is_active():
		time.sleep(0.1)

	stream.stop_stream()
	stream.close()
	audio.terminate()