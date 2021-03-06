import hashlib
import scipy
import scipy.io.wavfile
from scipy.fftpack import fft, rfft, fft2, dct
from python_speech_features import mfcc
import time
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import confusion_matrix
import numpy as np
import itertools
import matplotlib as mpl
import matplotlib.pyplot as plt
from config.config import *
import wave
import audioop

def feature_engineering( wavFile ):
	fs, rawWav = scipy.io.wavfile.read( wavFile )
	intensity = get_highest_intensity_of_wav_file( wavFile )
	
	return feature_engineering_raw( rawWav[:,0], fs, intensity )
	
def feature_engineering_raw( wavData, sampleRate, intensity ):
	mfcc_result1 = mfcc( wavData, samplerate=sampleRate, nfft=1103, numcep=13, appendEnergy=True )
	data_row = []
	data_row.extend( mfcc_result1.ravel() )
	freq = get_loudest_freq( wavData, RECORD_SECONDS )
	data_row.append( freq )
	data_row.append( intensity )
		
	return data_row, freq
	
def get_label_for_directory( setdir ):
	return float( int(hashlib.sha256( setdir.encode('utf-8')).hexdigest(), 16) % 10**8 )

def cross_validation( classifier, dataset, labels):
	return cross_val_score(classifier, dataset, labels, cv=5)

def average_prediction_speed( classifier, dataset_x ):
	start_time = time.time() * 1000
	classifier.predict( dataset_x[-1000:] )
	end_time = time.time() * 1000
	return int( end_time - start_time ) / len(dataset_x)
	
def create_confusion_matrix(classifier, dataset_x, dataset_labels, all_labels):
	X_train, X_test, y_train, y_test = train_test_split(dataset_x, dataset_labels, random_state=1)
	classifier.fit( X_train, y_train )
	y_pred = classifier.predict( X_test )

	cnf_matrix = confusion_matrix(y_test, y_pred)
	np.set_printoptions(precision=2)
	plot_confusion_matrix(cnf_matrix, all_labels )
	
def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize: 
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True category')
    plt.xlabel('Predicted category')
    plt.show()
	
def get_highest_intensity_of_wav_file( wav_file ):
	intensity = []
	with wave.open( wav_file ) as fd:
		params = fd.getparams()
		for i in range( 0, int(RATE / CHUNK * RECORD_SECONDS)):
			data = fd.readframes(CHUNK)
			peak = audioop.maxpp( data, 4 ) / 32767
			intensity.append( peak )
	
	return np.amax( intensity )
		
def get_loudest_freq( fftData, recordLength ):
	fft_result = fft( fftData )
	positiveFreqs = np.abs( fft_result[ 0:round( len(fft_result)/2 ) ] )
	highestFreq = 0
	loudestPeak = 500
	frequencies = [0]
	for freq in range( 0, len( positiveFreqs ) ):
		if( positiveFreqs[ freq ] > loudestPeak ):
			loudestPeak = positiveFreqs[ freq ]
			highestFreq = freq
	
	if( loudestPeak > 500 ):
		frequencies.append( highestFreq )
	
	if( recordLength < 1 ):
		# Considering our sound sample is, for example, 100 ms, our lowest frequency we can find is 10Hz ( I think )
		# So add that as a base to our found frequency to get Hz - This is probably wrong
		freqInHz = ( 1 / recordLength ) + np.amax( frequencies )
	else:
		# I have no clue how to even pretend to know how to calculate Hz for fft frames longer than a second
		freqInHz = np.amax( frequencies )
		
	return freqInHz

def get_recording_power( fftData, recordLength ):
	return audioop.rms( fftData, 4 ) / 1000
	
	
#def generate_tnse( dataset_x, dataset_labels ):
	#tsne = TSNE(n_components=2, verbose=1, perplexity=40, n_iter=300)
	#tsne_results = tsne.fit_transform( dataset_x, dataset_labels )

	#feat_cols = [ 'pixel'+str(i) for i in range(pandas.DataFrame(dataset_x).shape[1]) ]
	#df = pandas.DataFrame(dataset_x,columns=feat_cols)
	#df['label'] = dataset_labels
	#df['label'].apply(lambda i: str(i))

	#df_tsne = df
	#df_tsne['x-tsne'] = tsne_results[:,0]
	#df_tsne['y-tsne'] = tsne_results[:,1]
	#chart = ggplot( df_tsne, aes(x='x-tsne', y='y-tsne', color='label') ) \
	#		+ geom_point(size=70,alpha=1) \
	#		+ ggtitle("tSNE dimensions colored by digit")
		
	#print( chart )