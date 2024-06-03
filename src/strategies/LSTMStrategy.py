from collections import deque

import torch
from nltk.stem import PorterStemmer
from nltk.tokenize import word_to_idx, word_tokenize

from src import logger
from src.bot import Bot


class SentimentStrategy(Bot):
    requires_news = True

    def __init__(self, weights_path=None):
        Bot.__init__(self, ["1m"])
        if weights_path:
            self.inner_model = torch.load(weights_path)
        else:
            self.inner_model = torch.nn.Sequential(
                torch.nn.Embedding(10000, 64, 0),
                torch.nn.LSTM(64, 128, batch_first=True),
                torch.nn.ReLU(),
                torch.nn.LSTM(128, 64, batch_first=True),
                torch.nn.ReLU(),
                torch.nn.Linear(64, 3),
            )
        self.stemmer = PorterStemmer()
        self.price_history = deque(maxlen=500)

    def _preprocessor(self, news):
        r = []
        for n in news:
            val = []
            for w in word_tokenize(n):
                w = self.stemmer.stem(w)
                val.append(word_to_idx(w))
            r.append(val)
        return torch.nn.utils.rnn.pad_sequence(torch.LongTensor(r))

    def strategy(self, action, open, close, high, low, volume, news=None):

        self.price_history.append([open[-1], close[-1], high[-1], low[-1], volume[-1]])

        def entry_callback(avg_price=close[-1]):
            long = True if self.exchange.get_position_size() > 0 else False
            logger.info(f"{'Long' if long else 'Short'} Entry Order Successful")

        news_input = self._preprocessor(news)
        prices_tensor = torch.tensor(list(self.price_history)).float().unsqueeze(0)
        combined_input = torch.cat((news_input, prices_tensor), dim=1)

        # Pass through the model
        logits = self.inner_model(combined_input)
        p = torch.functional.softmax(logits, dim=-1).argmax(dim=-1)
        lot = self.exchange.get_lot()

        if p == 0:
            self.exchange.entry("Long", True, lot, callback=entry_callback)
        elif p == 1:
            pass
        elif p == 2:
            self.exchange.entry("Short", False, lot, callback=entry_callback)
