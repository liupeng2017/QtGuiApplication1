import io
import collections
import sys

from keras.preprocessing.sequence import pad_sequences
from keras.preprocessing.text import Tokenizer
import numpy as np

import matplotlib.pyplot as plt

#准备数据
poetry_file ='poetry.txt'

# 诗集
poems = []
with io.open(poetry_file, "r", encoding='utf-8',) as f:
    for line in f:
        try:
            title, content = line.strip().split(u':')
            content = content.replace(u' ',u'')
            if '_' in content or u'(' in content or u'（' in content or u'《' in content or u'[' in content:
                continue
            if len(content) < 5 or len(content) > 79:
                continue
            content = u'[' + content + u']'
            poems.append(content)
        except Exception as e:
            pass


# 按诗的字数排序
poems = sorted(poems, key=lambda line: len(line))
MAX_LEN = max(map(len, poems))
print('唐诗总数: ', len(poems))

spaced_poems = list(map(lambda poem: ' '.join(poem), poems))

partial_poems = []
next_chars = []
for poem in poems:
    for i in range(1, len(poem)):
        partial_poems.append(poem[:i])
        next_chars.append(poem[i])

# 统计每个字出现次数
# all_words = []
# for poem in poems:
#     all_words += [word for word in poem]
# counter = collections.Counter(all_words)
# count_pairs = sorted(counter.items(), key=lambda x: -x[1])
# words, _ = zip(*count_pairs)

#词法分析器
tokenizer = Tokenizer(lower=False, filters='')
#要用以训练的文本列表
tokenizer.fit_on_texts(spaced_poems)
#序列的列表，列表中每个序列对应于一段输入文本
#padding：‘pre’或‘post’，确定当需要补0时，在序列的起始还是结尾补
#truncating：‘pre’或‘post’，确定当需要截断序列时，从起始还是结尾截断
to_seq = lambda x: pad_sequences(tokenizer.texts_to_sequences(x), maxlen=MAX_LEN, padding='pre')

def batch_cycle_generator(texts, next_chars, batch_size, tokenizer, max_len):
    n = len(texts)
    n_words = len(tokenizer.word_counts)
    ind = 0
    while True:
        batch_texts = []
        batch_next_chars = []
        for _ in range(batch_size):
            batch_texts.append(texts[ind])
            batch_next_chars.append(next_chars[ind])
            ind = (ind + 1) % n
#         print(batch_texts)
        x_batch = pad_sequences(tokenizer.texts_to_sequences(map(lambda text: ' '.join(text), batch_texts)), maxlen=max_len, padding='pre')
        #向量化文本，形如(len(texts), nb_words)的numpy array
        y_batch = tokenizer.texts_to_matrix(batch_next_chars)
        yield (x_batch, y_batch)

# x = to_seq(spaced_poems)
# y = np.zeros(x.shape, dtype=np.int32)
# y[:, :-1] = x[:, 1:]

# x = to_seq(map(lambda poem: ' '.join(poem), partial_poems))
# y = tokenizer.texts_to_matrix(next_chars)
# 参数
UNITS = 128
N_LAYERS = 2
DIM_EMBED = 50
VOCAB = len(tokenizer.word_counts) + 1
BATCH_SIZE = 64

#建模
import keras
from keras.layers import Dense, Activation, LSTM, GRU, SimpleRNN, Input, Embedding, Dropout
from keras.models import Model

input_shape = (MAX_LEN, )
input_layer = Input(shape=input_shape)
z = input_layer

z = Embedding(VOCAB, DIM_EMBED, input_length=MAX_LEN, trainable=True)(z)
z = Dropout(0.4)(z)

z = GRU(UNITS, return_sequences=True)(z)
z = GRU(UNITS)(z)
z = Dense(VOCAB)(z)
z = Activation('softmax')(z)

model = Model(input_layer, z)
model.compile(
    loss=keras.losses.categorical_crossentropy,
    optimizer=keras.optimizers.RMSprop(),
)

model.summary()

#训练并观察结果
gen = batch_cycle_generator(partial_poems, next_chars, BATCH_SIZE, tokenizer, MAX_LEN)
def sample(preds, temperature=1.0):
    # helper function to sample an index from a probability array
    preds = np.asarray(preds).astype('float64')
    preds = np.log(preds) / temperature
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)
#     probas = np.random.multinomial(1, preds, 1)
#     return np.argmax(probas)
    #通过给定的一维数组数据产生随机采样
    return np.random.choice(len(preds), p=preds)

indices_char = {v: k for k, v in tokenizer.word_index.items()}

losses = []
# range(61)
for iteration in range(26):
    print()
    print('-' * 50)
    print('Iteration', iteration)
    #一个epoch分成多少个batch_size
    train_info = model.fit_generator(gen, 1000, epochs=1)
    losses.append(train_info.history['loss'][0])

    if iteration % 5 == 0:
        print('Generating text')
        for diversity in [0.2, 0.5, 1.0, 1.2]:
    #     for diversity in [0.2, 0.5, 1.0]:
            print()
            print('----- diversity:', diversity)

            generated = '['
            print('----- Generating with seed: "' + generated + '"')
            sys.stdout.write(generated)

            for i in range(81):
                ##sequences to (num_samples, num_timesteps)
                x = pad_sequences(tokenizer.texts_to_sequences([' '.join(generated)]), maxlen=MAX_LEN, padding='pre')

                preds = model.predict(x, verbose=0)[0]
                next_index = sample(preds, diversity)
                next_char = indices_char[next_index]

                generated += next_char

                sys.stdout.write(next_char)
                sys.stdout.flush()
                if next_char == ']':
                    break
            print()

plt.plot(losses)
plt.xlabel('epoch')
plt.ylabel('loss')
plt.grid()
model.save('poet_2gru_26epochs.h5')






