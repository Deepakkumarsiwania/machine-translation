# -*- coding: utf-8 -*-
"""dl_ass2_question2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19r96FvFAQzwrQb-Z7rEWPMU1niVoMZ98
"""

# Commented out IPython magic to ensure Python compatibility.

#-- Necessary Imports
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import datetime as dt
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
import matplotlib as mpl
# %matplotlib inline
from sklearn.preprocessing import MinMaxScaler
from random import random

# Load the dataset
df = pd.read_csv('household_power_consumption.txt', sep=';', 
                 parse_dates={'DateTime': ['Date', 'Time']}, 
                 infer_datetime_format=True, low_memory=False)

# Drop rows with missing values
df.dropna(inplace=True)

# Set DateTime as index
df.set_index('DateTime', inplace=True)

# Split dataset into train and test sets
train_size = int(len(df) * 0.8)

train_data = df[:train_size]
test_data = df[train_size:]

print(train_data.shape)

# Normalize the dataset
scaler = MinMaxScaler()
train_data = scaler.fit_transform(train_data)
test_data = scaler.transform(test_data)

df

df.head()
df.dtypes
# 11 variable(cols) has yes or no values.

# checking for null data --> No null data
df.info()
df.isnull().sum()

train_data.dtype

df.columns

for j in range(1,7):
       print(df.iloc[:, j].unique())

df['Global_active_power'].resample('M').sum()

df['Global_active_power'] = pd.to_numeric(df['Global_active_power'], errors='coerce')

df.Global_active_power.resample('D').sum().plot(title='Global_active_power resampled over day for sum') 
#df.Global_active_power.resample('D').mean().plot(title='Global_active_power resampled over day', color='red') 
plt.tight_layout()
plt.show()   

df.Global_active_power.resample('D').mean().plot(title='Global_active_power resampled over day for mean', color='red') 
plt.tight_layout()
plt.show()

df['Global_intensity'] = pd.to_numeric(df['Global_intensity'], errors='coerce')

r = df.Global_intensity.resample('D').agg(['mean', 'std'])
r.plot(subplots = True, title='Global_intensity resampled over day')
plt.show()

"""Step 3: Create input sequences and corresponding target values for training the LSTM model"""

def create_sequences(data, seq_length):
    xs = []
    ys = []
    for i in range(len(data)-seq_length-1):
        x = data[i:(i+seq_length), :]
        y = data[(i+seq_length), 0]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

seq_length = 30 # Define the length of input sequence
train_X, train_y = create_sequences(train_data, seq_length)
test_X, test_y = create_sequences(test_data, seq_length)

class LSTM(nn.Module):
    def __init__(self, input_size, hidden_size, seq_length, num_layers):
        super(LSTM, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.seq_length = seq_length
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

# Define hyperparameters
input_size = train_X.shape[2]
hidden_size = 64
num_layers = 2
learning_rate = 0.001
batch_size = 64
num_epochs = 6

# Convert numpy arrays to PyTorch tensors
train_X = torch.from_numpy(train_X).float()
train_y = torch.from_numpy(train_y).float()
test_X = torch.from_numpy(test_X).float()
test_y = torch.from_numpy(test_y).float()

# Create data loaders
train_dataset = torch.utils.data.TensorDataset(train_X, train_y)
train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_dataset = torch.utils.data.TensorDataset(test_X, test_y)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# Initialize the model and optimizer
device = torch.device('cuda' if torch.cuda.is_available() else torch.device('cpu'))

print(device)

# Define the model, loss function, and optimizer
model = LSTM(input_size, hidden_size, seq_length, num_layers).to(device)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

# Train the model
train_losses = []
test_losses = []
for epoch in range(num_epochs):
    train_loss = 0.0
    test_loss = 0.0
    model.train()
    for i, (inputs, targets) in enumerate(train_loader):
        inputs = inputs.to(device)
        targets = targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        train_loss += loss.item() * inputs.size(0)
    train_loss /= len(train_loader.dataset)
    train_losses.append(train_loss)
    
    model.eval()
    with torch.no_grad():
        for i, (inputs, targets) in enumerate(test_loader):
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            test_loss += loss.item() * inputs.size(0)
        test_loss /= len(test_loader.dataset)
        test_losses.append(test_loss)
    
    # Print the losses at the end of each epoch
    print(f'Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.6f}, Test Loss: {test_loss:.6f}')

# Plot the train and test losses
plt.plot(train_losses, label='Train Loss')
plt.plot(test_losses, label='Test Loss')
plt.legend()
plt.show()

# Make predictions on the test set
 model.eval()
 with torch.no_grad():
     test_inputs = test_X.to(device)
     test_outputs = model(test_inputs)
     test_predictions = test_outputs.cpu().numpy()

 # Invert the scaling on the test set and predictions
 test_predictions = scaler.inverse_transform(np.concatenate((test_predictions, np.zeros((test_predictions.shape[0], 7))), axis=1))[:, 0]
 test_actual = scaler.inverse_transform(np.concatenate((test_y.reshape(-1, 1), np.zeros((test_y.shape[0], 7))), axis=1))[:, 0]

 # Plot the actual and predicted values for the test set
 plt.plot(test_actual, label='Actual')
 plt.plot(test_predictions, label='Predicted')
 plt.legend()
 plt.show()

# Split dataset into train and test sets
train_size = int(len(df) * 0.7)

train_data1 = df[:train_size]
test_data1 = df[train_size:]

train_data1.shape

scaler = MinMaxScaler()
train_data1 = scaler.fit_transform(train_data1)
test_data1 = scaler.transform(test_data1)

df['Global_active_power'] = pd.to_numeric(df['Global_active_power'], errors='coerce')

df.Global_active_power.resample('D').sum().plot(title='Global_active_power resampled over day for sum') 
#df.Global_active_power.resample('D').mean().plot(title='Global_active_power resampled over day', color='red') 
plt.tight_layout()
plt.show()   

df.Global_active_power.resample('D').mean().plot(title='Global_active_power resampled over day for mean', color='red') 
plt.tight_layout()
plt.show()

def create_sequences1(data, seq_length):
    xs = []
    ys = []
    for i in range(len(data)-seq_length-1):
        x = data[i:(i+seq_length), :]
        y = data[(i+seq_length), 0]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

seq_length = 30 # Define the length of input sequence
train_X, train_y = create_sequences1(train_data, seq_length)
test_X, test_y = create_sequences1(test_data, seq_length)

class LSTM1(nn.Module):
    def __init__(self, input_size, hidden_size, seq_length, num_layers):
        super(LSTM1, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.seq_length = seq_length
        self.num_layers = num_layers
        self.lstm = nn.LSTM1(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

# Define hyperparameters
input_size = train_X.shape[2]
hidden_size = 64
num_layers = 2
learning_rate = 0.001
batch_size = 64
num_epochs = 5

# Convert numpy arrays to PyTorch tensors
train_X = torch.from_numpy(train_X).float()
train_y = torch.from_numpy(train_y).float()
test_X = torch.from_numpy(test_X).float()
test_y = torch.from_numpy(test_y).float()

# Create data loaders
train_dataset = torch.utils.data.TensorDataset(train_X, train_y)
train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_dataset = torch.utils.data.TensorDataset(test_X, test_y)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# Initialize the model and optimizer
device = torch.device('cuda' if torch.cuda.is_available() else torch.device('cpu'))

print(device)

#Define the model, loss function, and optimizer
model1 = LSTM(input_size, hidden_size, seq_length, num_layers).to(device)
criterion = nn.MSELoss()
optimizer1 = torch.optim.Adam(model.parameters(), lr=learning_rate)

# Train the model
train_losses = []
test_losses = []
for epoch in range(num_epochs):
    train_loss = 0.0
    test_loss = 0.0
    model1.train()
    for i, (inputs, targets) in enumerate(train_loader):
        inputs = inputs.to(device)
        targets = targets.to(device)
        optimizer1.zero_grad()
        outputs = model1(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer1.step()
        train_loss += loss.item() * inputs.size(0)
    train_loss /= len(train_loader.dataset)
    train_losses.append(train_loss)
    
    model.eval()
    with torch.no_grad():
        for i, (inputs, targets) in enumerate(test_loader):
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model1(inputs)
            loss = criterion(outputs, targets)
            test_loss += loss.item() * inputs.size(0)
        test_loss /= len(test_loader.dataset)
        test_losses.append(test_loss)
    
    # Print the losses at the end of each epoch
    print(f'Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.6f}, Test Loss: {test_loss:.6f}')

# Plot the train and test losses
plt.plot(train_losses, label='Train Loss')
plt.plot(test_losses, label='Test Loss')
plt.legend()
plt.show()

"""**queation 1**"""

dataset_test=pd.read_csv("/content/drive/MyDrive/Dataset/Dakshina Dataset/hi/lexicons/hi.translit.sampled.test.tsv",sep='\t',header=None, names=['hindi', 'eng','5'])
dataset_train =pd.read_csv("/content/drive/MyDrive/Dataset/Dakshina Dataset/hi/lexicons/hi.translit.sampled.train.tsv",sep='\t',header=None, names=['hindi', 'eng','3'])



dataset_train.dropna(inplace=True)
dataset_test.dropna(inplace=True)

dataset_train

dataset_test

dataset_train.head()

df_train = dataset_train.drop("3", axis=1)


# Print the resulting dataframe
print(df_train.head())

df_test = dataset_test.drop("5", axis=1)

df_train.dtypes
# 11 variable(cols) has yes or no values.

# checking for null data --> No null data
df_train.info()
df_train.isnull().sum()

df_train.dtypes



# import nltk

# german_tokenizer = nltk.data.load('/content/drive/MyDrive/Dataset/Dakshina Dataset/hi/lexicons/hi.translit.sampled.train.tsv')
# german_tokens=german_tokenizer.tokenize()
# print(german_tokens)

pip install indic-nlp-library

# hindi_tokens = []
# for i in df_train.index:
#   hindi_tokens.append(indic_tokenize.trivial_tokenize(df_train["hindi"][i]))

# hindi_tokens

hindi_tokens = []
for i in df_test.index:
  for char in df_test['hindi'][i]:
    hindi_tokens.extend(char)
  
hindi_token = sorted(set(hindi_tokens))
  # hindi_tokens.extend(df_train["hindi"][i].unique())

hindi_tokens = list(set(hindi_tokens)) 
print(hindi_tokens)

hindi_dict = dict()
hindi_dict['SOS'] = 1
hindi_dict['EOS'] = 2

for i, char in enumerate(hindi_token):
  hindi_dict[char] = i+3

hindi_dict #test

hindi_tokens = []
for i in df_train.index:
  for char in df_train['hindi'][i]:
    hindi_tokens.extend(char)
  
hindi_token = sorted(set(hindi_tokens))
  # hindi_tokens.extend(df_train["hindi"][i].unique())

hindi_tokens = list(set(hindi_tokens)) 
print(hindi_tokens)

hindi_dict = dict()
hindi_dict['SOS'] = 1
hindi_dict['EOS'] = 2

for i, char in enumerate(hindi_token):
  hindi_dict[char] = i+3

hindi_dict

eng_tokens = []
for i in df_test.index:
  for char in df_test['eng'][i]:
    eng_tokens.extend(char)
  
eng_token = sorted(set(eng_tokens))
  # hindi_tokens.extend(df_train["hindi"][i].unique())

# hindi_tokens = list(set(eng_tokens)) 
print(eng_token)


eng_dict = dict()

eng_dict['SOS'] = 1
eng_dict['EOS'] = 2
for i, char in enumerate(eng_token):
  eng_dict[char] = i+3

eng_dict #test

eng_tokens = []
for i in df_train.index:
  for char in df_train['eng'][i]:
    eng_tokens.extend(char)
  
eng_token = sorted(set(eng_tokens))
  # hindi_tokens.extend(df_train["hindi"][i].unique())

# hindi_tokens = list(set(eng_tokens)) 
print(eng_token)


eng_dict = dict()

eng_dict['SOS'] = 1
eng_dict['EOS'] = 2
for i, char in enumerate(eng_token):
  eng_dict[char] = i+3

eng_dict

eng_tensor_ls_test = []
for i in df_test.index:
  x = df_test['eng'][i]
  eng_tensor = []
  eng_tensor.append(eng_dict['SOS'])
  for char in x:
    eng_tensor.append(eng_dict[char])
  eng_tensor.append(eng_dict['EOS'])
  eng_tensor = torch.tensor(eng_tensor)
  
  
  eng_tensor_ls_test.append(eng_tensor)
#eng_tensor
eng_tensor_ls_test

eng_tensor_ls = []
for i in df_train.index:
  x = df_train['eng'][i]
  eng_tensor = []
  eng_tensor.append(eng_dict['SOS'])
  for char in x:
    eng_tensor.append(eng_dict[char])
  eng_tensor.append(eng_dict['EOS'])
  eng_tensor = torch.tensor(eng_tensor)
  
  
  eng_tensor_ls.append(eng_tensor)
#eng_tensor
eng_tensor_ls

import torch
from torch.nn.utils.rnn import pad_sequence
padded_tensor_E = pad_sequence(eng_tensor_ls, batch_first=True)

# Print the padded tensor
print(padded_tensor_E.shape)

import torch
from torch.nn.utils.rnn import pad_sequence
padded_tensor_E_Test = pad_sequence(eng_tensor_ls_test, batch_first=True)

# Print the padded tensor
print(padded_tensor_E_Test.shape)

hindi_tensor_ls = []
for i in df_train.index:
  x = df_train['hindi'][i]
  hin_tensor = []
  hin_tensor.append(eng_dict['SOS'])
  for char in x:
    hin_tensor.append(hindi_dict[char])
  hin_tensor.append(eng_dict['EOS'])

  hin_tensor = torch.tensor(hin_tensor)

  hindi_tensor_ls.append(hin_tensor)

#hindi_tensor_ls = torch.tensor(hindi_tensor_ls)

print(hindi_tensor_ls[0])

hindi_tensor_ls_test = []
for i in df_test.index:
  x = df_test['hindi'][i]
  hin_tensor = []
  hin_tensor.append(eng_dict['SOS'])
  for char in x:
    hin_tensor.append(hindi_dict[char])
  hin_tensor.append(eng_dict['EOS'])

  hin_tensor = torch.tensor(hin_tensor)

  hindi_tensor_ls_test.append(hin_tensor)

#hindi_tensor_ls = torch.tensor(hindi_tensor_ls)

print(hindi_tensor_ls_test[0])

import torch
from torch.nn.utils.rnn import pad_sequence

padded_tensor_Test = pad_sequence(hindi_tensor_ls_test, batch_first=True)

# Print the padded tensor
print(padded_tensor_Test.shape)

padded_tensor_H = pad_sequence(hindi_tensor_ls, batch_first=True)

# Print the padded tensor
print(padded_tensor_H.shape)

padded_tensor_H_Test = pad_sequence(hindi_tensor_ls_test, batch_first=True)

# Print the padded tensor
print(padded_tensor_H_Test.shape)

padded_tensor_T = pad_sequence([padded_tensor_E.T, padded_tensor_H.T], batch_first=True)

padded_tensor_TET= pad_sequence([padded_tensor_E_Test.T, padded_tensor_H_Test.T], batch_first=True)

en = padded_tensor_T[0].T
hi = padded_tensor_T[1].T

hi[2], en[2]

en1 = padded_tensor_TET[0].T
hi1 = padded_tensor_TET[1].T

hi1[2], en1[2]

class CustomDataset(Dataset):
  def __init__(self,padded_tensor_T):
    self.hi = padded_tensor_T[1].T
    self.en = padded_tensor_T[0].T

  def __len__(self):
    return len(self.hi)

  def __getitem__(self, index):
     return self.en[index], self.hi[index]

class CustomDataset1(Dataset):
  def __init__(self,padded_tensor_TET):
    self.hi1 = padded_tensor_TET[1].T
    self.en1 = padded_tensor_TET[0].T

  def __len__(self):
    return len(self.hi1)

  def __getitem__(self, index):
     return self.en1[index], self.hi1[index]

train_data = CustomDataset(padded_tensor_T)
train_data.__getitem__(2)

train_data1= CustomDataset1(padded_tensor_TET)
train_data.__getitem__(2)

trainloader = DataLoader(train_data, batch_size = 5, shuffle = True, drop_last = True)

testloader = DataLoader(train_data1, batch_size = 5, shuffle = True, drop_last = True)

for i, batch in enumerate(trainloader):
  en, hi = batch
  en = en.T
  hi = hi.T

for i, batch in enumerate(testloader):
  en1, hi1 = batch
  en1 = en1.T
  hi1 = hi1.T

class Encoder(nn.Module):
    def __init__(self, input_size, embedding_size, hidden_size, num_layers, p):
        super(Encoder, self).__init__()
        self.dropout = nn.Dropout(p)
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.embedding = nn.Embedding(input_size, embedding_size)
        self.rnn = nn.LSTM(embedding_size, hidden_size, num_layers, dropout=p)

    def forward(self, x):
        # x shape: (seq_length, N) where N is batch size

        embedding = self.dropout(self.embedding(x))
        # embedding shape: (seq_length, N, embedding_size)

        outputs, (hidden, cell) = self.rnn(embedding)
        # outputs shape: (seq_length, N, hidden_size)

        return hidden, cell


class Decoder(nn.Module):
    def __init__(
        self, input_size, embedding_size, hidden_size, output_size, num_layers, p
    ):
        super(Decoder, self).__init__()
        self.dropout = nn.Dropout(p)
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.embedding = nn.Embedding(input_size, embedding_size)
        self.rnn = nn.LSTM(embedding_size, hidden_size, num_layers, dropout=p)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x, hidden, cell):
        # x shape: (N) where N is for batch size, we want it to be (1, N), seq_length
        # is 1 here because we are sending in a single word and not a sentence
        x = x.unsqueeze(0)

        embedding = self.dropout(self.embedding(x))
        # embedding shape: (1, N, embedding_size)

        outputs, (hidden, cell) = self.rnn(embedding, (hidden, cell))
        # outputs shape: (1, N, hidden_size)

        predictions = self.fc(outputs)

        # predictions shape: (1, N, length_target_vocabulary) to send it to
        # loss function we want it to be (N, length_target_vocabulary) so we're
        # just gonna remove the first dim
        predictions = predictions.squeeze(0)

        return predictions, hidden, cell


class Seq2Seq(nn.Module):
    def __init__(self, encoder, decoder):
        super(Seq2Seq, self).__init__()
        self.encoder = encoder
        self.decoder = decoder

    def forward(self, source, target, teacher_force_ratio=0.5):
        batch_size = source.shape[1]
        target_len = target.shape[0]
        target_vocab_size = 1000

        outputs = torch.zeros(target_len, batch_size, target_vocab_size).to(device)

        hidden, cell = self.encoder(source)

        # Grab the first input to the Decoder which will be <SOS> token
        x = target[0]

        for t in range(1, target_len):
            # Use previous hidden, cell as context from encoder at start
            output, hidden, cell = self.decoder(x, hidden, cell)

            # Store next output prediction
            outputs[t] = output

            # Get the best word the Decoder predicted (index in the vocabulary)
            best_guess = output.argmax(1)

            # With probability of teacher_force_ratio we take the actual next word
            # otherwise we take the word that the Decoder predicted it to be.
            # Teacher Forcing is used so that the model gets used to seeing
            # similar inputs at training and testing time, if teacher forcing is 1
            # then inputs at test time might be completely different than what the
            # network is used to. This was a long comment.
            x = target[t] if random.random() < teacher_force_ratio else best_guess

        return outputs



# import torch
# import torch.nn as nn
# import random as random

# class Encoder(nn.Module):
#     def __init__(self, input_size_encoder, embedding_dim, hidden_dim):
#         super(Encoder, self).__init__()
#         self.hidden_dim = hidden_dim
#         self.embedding = nn.Embedding(input_size_encoder, embedding_dim)
#         self.lstm = nn.LSTM(embedding_dim, hidden_dim, num_layers=2 )
        

#     def forward(self, input_seq):
#         print(input_seq.shape)
#         embedded = self.embedding(input_seq)
#         print(embedded.shape)
#         outputs, (hidden, cell) = self.lstm(embedded)
#         print(outputs.shape)
#         print(hidden.shape)
#         print("encoder pass")
#         return hidden, cell

# class Decoder(nn.Module):
#     def __init__(self, output_size, embedding_dim, hidden_dim):
#         super(Decoder, self).__init__()
#         self.hidden_dim = hidden_dim
#         self.embedding = nn.Embedding(output_size, embedding_dim)
#         self.lstm = nn.LSTM(embedding_dim, hidden_dim,num_layers=2)
#         self.fc = nn.Linear(hidden_dim, output_size)

#     def forward(self, input_seq, hidden, cell):
#         print("decoder in")
#         #input_seq = input_seq.unsqueeze(0)
#         embedded = self.embedding(input_seq)
#         #print(embedded.shape)
#         outputs, (hidden, cell) = self.lstm(embedded, (hidden, cell))

#         predictions = self.fc(outputs)
#         print("decoder pass")
#         return predictions, hidden, cell

# class Seq2Seq(nn.Module):
#     def __init__(self, encoder, decoder):
#         super(Seq2Seq, self).__init__()
#         self.encoder = encoder
#         self.decoder = decoder

#     def forward(self, input_seq, target_seq, teacher_forcing_ratio=0.5):
#         batch_size = target_seq.shape[1]
#         target_len = target_seq.shape[0]
#         target_vocab_size = self.decoder.fc.out_features
#         outputs = torch.zeros(target_len, batch_size, target_vocab_size).to(device)
#         hidden, cell = self.encoder(input_seq)
#         input_x = target_seq[0]
#         print(input_x.shape)
#         for t in range(0, 22):
#             output, hidden, cell = self.decoder(input_x, hidden, cell)
#             #print(hidden.shape)
#             #print(output.shape)
#             outputs[t] = output
#             top1 = output.argmax(1)
#             #teacher_force = random.random() < teacher_forcing_ratio
            
#             input_x = target_seq[t] if random.random() < teacher_forcing_ratio else top1 
      
#         return outputs

#traing
num_epochs=3
lr=.001
batch_size=64
#model hyperamter
load_model=False
device=torch.device('cuda'if torch.cuda.is_available()else'cpu')
input_size_encoder=1000
input_size_decoder=1000
output_size=1000
embedding_dim=300
embedding_dim=300
hidden_dim=1024
num_layers=2
encoder_droupout=0.5
decoder_droupout=0.5
input_size=100 
embedding_size=300 
hidden_size=300 
num_layers=2


step=0
encoder_net=Encoder(input_size_encoder, embedding_size, hidden_size, num_layers, encoder_droupout
).to(device)
decoder_net = Decoder(
    input_size_decoder,
    embedding_size,
    hidden_size,
    output_size,
    num_layers,
    decoder_droupout
).to(device)
#decoder_net=Decoder(input_size_encoder, embedding_size, hidden_size, num_layers, decoder_droupout).to(device)
model2=Seq2Seq(encoder_net,decoder_net).to(device)

print(len(en))

print(device)

criterion=nn.CrossEntropyLoss()
optimizer = optim.Adam(model2.parameters(), lr=.001)

i=0
for x , y in trainloader:
 i+=1
print(i)

# training loop
import random
for epoch in range(num_epochs):
    epoch_loss = 0
    for batch in trainloader:
      en, hi = batch
      input_seq = en.T.to(device)
      #print(input_seq.shape)

      #print(f"input:{input_seq}")
      #input_seq=input_seq.reshape(-1,1000)
      target_seq = hi.T.to(device)
      #print(target_seq.shape)
      #print(f"target:{target_seq}")

      #target_seq=target_seq.reshape(-1,1000)

      #print(input_seq.shape, target_seq.shape)
      optimizer.zero_grad()

      output = model2(input_seq, target_seq)
      #print("pass")
      #print(f"output: {output}")
      output= output[1:].reshape(-1,output.shape[2])

      target_seq=target_seq[1:].reshape(-1)
      loss=criterion(output,target_seq)
      loss.backward()
      optimizer.step()
      epoch_loss += loss.item()
    print('Epoch {}, Loss: {}/100'.format(epoch+1, epoch_loss))