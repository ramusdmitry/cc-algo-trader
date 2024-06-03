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
                torch.nn.MultiheadAttention(64, 3, kdim=100, vdim=100),
                torch.nn.ReLU(),
                torch.nn.MultiheadAttention(64, 3, kdim=100, vdim=100),
                torch.nn.ReLU(),
                torch.nn.Linear(100, 3),
            )
        self.stemmer = PorterStemmer()

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
        def entry_callback(avg_price=close[-1]):
            long = True if self.exchange.get_position_size() > 0 else False
            logger.info(f"{'Long' if long else 'Short'} Entry Order Successful")

        logits = self.inner_model(self._preprocessor(news))
        p = torch.functional.softmax(logits).argmax()
        lot = self.exchange.get_lot()
        if p == 0:
            self.exchange.entry("Long", True, lot, callback=entry_callback)
        elif p == 1:
            pass
        elif p == 2:
            self.exchange.entry("Short", False, lot, callback=entry_callback)
