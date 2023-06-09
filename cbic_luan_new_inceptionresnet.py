from google.colab import drive

drive.mount('/content/gdrive')
root_path = './gdrive/My Drive/Faculdade/CBIC_LUAN'

from __future__ import print_function
import keras
from keras.layers import Dense, Conv2D, BatchNormalization, Activation, Dropout
from keras.layers import AveragePooling2D, Input, Flatten, GlobalAveragePooling2D
from keras.optimizers import Adam
from keras.callbacks import ModelCheckpoint, LearningRateScheduler
from keras.callbacks import ReduceLROnPlateau
from keras.preprocessing.image import ImageDataGenerator
from keras.regularizers import l2
from keras import backend as K
from keras.models import Model
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from keras.utils.np_utils import to_categorical # convert to one-hot-encoding
import numpy as np
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
import h5py
from mlxtend.plotting import plot_confusion_matrix
from keras.applications.inception_v3 import InceptionV3
from keras.applications.resnet50 import ResNet50
from keras.applications.inception_resnet_v2 import InceptionResNetV2
from keras_applications.resnext import ResNeXt50
from keras.applications.vgg16 import VGG16
import os
import glob

ext_img = '.jpg'
num_px = 75
num_py = 75
total_imgs = 5856     # total of images considering all classes
base_name = '/content/gdrive/My Drive/Faculdade/CBIC_LUAN' # main folder

# Training parameters
batch_size = 16  # orig paper trained all networks with batch_size=128
epochs = 200
data_augmentation = True
num_classes = 2

# Subtracting pixel mean improves accuracy
subtract_pixel_mean = True

# Load data
hf = h5py.File(os.path.join(base_name, 'base_antiga.h5'), 'r')
x_train = np.array(hf.get('x_train'))
x_test = np.array(hf.get('x_test'))
y_train = np.array(hf.get('y_train'))
y_test = np.array(hf.get('y_test'))

labels_dic = {}
for l in hf.keys():
    if 'x_train' not in l and 'x_test' not in l and 'y_train' not in l and 'y_test' not in l:
        print(hf[l].value)
        print(l)
        labels_dic[hf[l].value] = l

hf.close()

print("Train shape" + str(x_train.shape))
print("Test shape" + str(x_test.shape))
#print("Label test: " + str(labels_dic[0]))

#n = 8

# Model version
# Orig paper: version = 1 (ResNet v1), Improved ResNet: version = 2 (ResNet v2)
#version = 1


# Model name, depth and version
#model_type = 'ResNet%dv%d' % (depth, version)

# Input image dimensions.
input_shape = x_train.shape[1:]

# Normalize data.
x_train = x_train.astype('float32') / 255
x_test = x_test.astype('float32') / 255

# If subtract pixel mean is enabled
if subtract_pixel_mean:
    x_train_mean = np.mean(x_train, axis=0)
    x_train -= x_train_mean
    x_test -= x_train_mean

print(x_train.shape[0], 'train samples')
print(x_test.shape[0], 'test samples')
print('x_train shape:', x_train.shape)
print('y_train shape:', y_train.shape)
print('x_test shape:', x_test.shape)
print('y_test shape:', y_test.shape)


# Convert class vectors to binary class matrices.
y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)


def lr_schedule(epoch):
    """Learning Rate Schedule

    Learning rate is scheduled to be reduced after 80, 120, 160, 180 epochs.
    Called automatically every epoch as part of callbacks during training.

    # Arguments
        epoch (int): The number of epochs

    # Returns
        lr (float32): learning rate
    """
    lr = 1e-3
    if epoch > 180:
        lr *= 0.5e-3
    elif epoch > 160:
        lr *= 1e-3
    elif epoch > 120:
        lr *= 1e-2
    elif epoch > 80:
        lr *= 1e-1
    print('Learning rate: ', lr)
    return lr
   
############################################################################################
#NEW PART
#base_model = VGG16(include_top=False, weights=None, input_tensor=None, input_shape=input_shape)
#base_model = InceptionV3(include_top=False, weights=None, input_tensor=None, input_shape=input_shape,
#base_model = ResNet50(include_top=False, weights=None, input_tensor=None, input_shape=input_shape)
base_model= InceptionResNetV2(include_top=False, weights=None, input_tensor=None, input_shape=input_shape)
#base_model= ResNeXt50(include_top=False, weights=None, input_shape=input_shape,
                            backend=keras.backend,
                            layers=keras.layers,
                            models=keras.models,
                            utils=keras.utils)

model_type = 'InceptionResNetV2'
directory_results = '/content/gdrive/Faculdade/CBIC_LUAN/resultados/'
model_name= 'InceptionResNetV2'

model = base_model.output
model = GlobalAveragePooling2D()(model)
model = Dense(128, activation='relu')(model)
model = Dropout(0.2)(model)

predictions = Dense(num_classes, activation='sigmoid',kernel_initializer='he_normal')(model)
model = Model(inputs=base_model.input, outputs=predictions)
#########################################################################
model.compile(loss='binary_crossentropy',
              optimizer=Adam(lr=lr_schedule(0)),
              metrics=['accuracy'])
model.summary()



# Prepare model model saving directory.
save_dir = os.path.join(base_name, 'saved_models')
model_name = 'XDB32_%s_model.{epoch:03d}.h5' % model_type
if not os.path.isdir(save_dir):
    os.makedirs(save_dir)
filepath = os.path.join(save_dir, model_name)

# Prepare callbacks for model saving and for learning rate adjustment.
checkpoint = ModelCheckpoint(filepath=filepath,
                             monitor='val_acc',
                             verbose=1,
                             save_best_only=True)

lr_scheduler = LearningRateScheduler(lr_schedule)

lr_reducer = ReduceLROnPlateau(factor=np.sqrt(0.1),
                               cooldown=0,
                               patience=5,
                               min_lr=0.5e-6)

callbacks = [checkpoint, lr_reducer, lr_scheduler]

# Run training, with or without data augmentation.
if not data_augmentation:
    print('Not using data augmentation.')
    h = model.fit(x_train, y_train,
              batch_size=batch_size,
              epochs=epochs,
              validation_data=(x_test, y_test),
              shuffle=True,
              callbacks=callbacks)
else:
    print('Using real-time data augmentation.')
    # This will do preprocessing and realtime data augmentation:
    datagen = ImageDataGenerator(
        # set input mean to 0 over the dataset
        featurewise_center=False,
        # set each sample mean to 0
        samplewise_center=False,
        # divide inputs by std of dataset
        featurewise_std_normalization=False,
        # divide each input by its std
        samplewise_std_normalization=False,
        # apply ZCA whitening
        zca_whitening=False,
        # epsilon for ZCA whitening
        zca_epsilon=1e-06,
        # randomly rotate images in the range (deg 0 to 180)
        rotation_range=0,
        # randomly shift images horizontally
        width_shift_range=0.1,
        # randomly shift images vertically
        height_shift_range=0.1,
        # set range for random shear
        shear_range=0.,
        # set range for random zoom
        zoom_range=0.,
        # set range for random channel shifts
        channel_shift_range=0.,
        # set mode for filling points outside the input boundaries
        fill_mode='nearest',
        # value used for fill_mode = "constant"
        cval=0.,
        # randomly flip images
        horizontal_flip=True,
        # randomly flip images
        vertical_flip=False,
        # set rescaling factor (applied before any other transformation)
        rescale=None,
        # set function that will be applied on each input
        preprocessing_function=None,
        # image data format, either "channels_first" or "channels_last"
        data_format=None,
        # fraction of images reserved for validation (strictly between 0 and 1)
        validation_split=0.0)

    # Compute quantities required for featurewise normalization
    # (std, mean, and principal components if ZCA whitening is applied).
    datagen.fit(x_train)

    # Fit the model on the batches generated by datagen.flow().
    h = model.fit_generator(datagen.flow(x_train, y_train, batch_size=batch_size),
                        steps_per_epoch=x_train.shape[0] // batch_size,
                        validation_data=(x_test, y_test),
                        validation_steps=x_test.shape[0] // batch_size,
                        epochs=epochs, verbose=1, workers=4,
                        callbacks=callbacks)

 


######################################################################################################


##Cria uma nova pasta para a respectiva execução

if os.path.exists(directory_results+model_name) == False:
  os.mkdir(directory_results+model_name)
     
directory_results = directory_results+model_name
tamanho_directory = len(directory_results)+1

lista = [os.path.join(directory_results, o) for o in os.listdir(directory_results) 
                    if os.path.isdir(os.path.join(directory_results,o))]
count = 0
for pasta in lista:
  count=int(pasta[tamanho_directory:])

count+=1
os.mkdir(directory_results+'/'+str(count))
directory_results = directory_results+'/'+str(count)+'/'






model.save_weights(os.path.join(directory_results,model_name+'.h5'))#save weights

print(h)
# History of acc(train) and val_acc(validation)
hist_acc_train = h.history['acc']
hist_loss_train = h.history['loss']
hist_acc_test = h.history['val_acc']
hist_loss_test = h.history['val_loss']

print('History of train\n', hist_acc_train)
print('History of test\n', hist_acc_test)

np.save(directory_results+model_name+'_acc_train.npy',hist_acc_train)
np.save(directory_results+model_name+'_loss_train.npy',hist_loss_train)
np.save(directory_results+model_name+'_acc_test.npy',hist_acc_test)
np.save(directory_results+model_name+'_loss_test.npy',hist_loss_test)


# plot history
plt.figure(1)
plt.plot(hist_loss_train)
plt.plot(hist_loss_test)
plt.legend(['Train loss','Test loss'], loc='upper right')
plt.title('Learning curves')

plt.figure(2)
plt.plot(hist_acc_train)
plt.plot(hist_acc_test)
plt.legend(['Train acc','Test acc'], loc='upper right')
plt.title('Accuracy')

# Report
pred_test = np.argmax(model.predict(x_test, batch_size=1, verbose=0), axis=1)
true_test = np.argmax(y_test, axis=1)
cf = confusion_matrix(true_test, pred_test)
print(cf)

np.save(directory_results+model_name+'_pred_test.npy',pred_test)
np.save(directory_results+model_name+'_true_test.npy',true_test)
np.save(directory_results+model_name+'_cf.npy',cf)


if(not os.path.exists(directory_results+model_name+'.txt')):
  file = open(directory_results+model_name+'.txt', 'w')
  file.close()

file = open(directory_results+model_name+'.txt', 'r')

lines = file.readlines()

results_class = []
for cl in range(num_classes):
  print("\n%s: %.2f%%" % (labels_dic[cl], cf[cl,cl]/sum(true_test==cl)*100))
  lines.append("\n%s: %.2f%%" % (labels_dic[cl], cf[cl,cl]/sum(true_test==cl)*100))
  results_class.append(cf[cl,cl]/sum(true_test==cl)*100)

np.save(directory_results+model_name+'_results_class.npy',results_class)
labels = []
for i in labels_dic:
  labels.append(labels_dic[i])
np.save(directory_results+model_name+'_labels.npy',labels)

print(labels_dic.values())
print(classification_report(true_test, pred_test, target_names=labels_dic.values()))
lines.append("\n"+str(classification_report(true_test, pred_test, target_names=labels_dic.values())))

# save file execution
file = open(directory_results+model_name+'.txt', 'w')
file.writelines(lines)
file.close()
