# DEEP DIVE — COIN (FinMem-Ours, test 2026-01-02 → 2026-06-01)

102 test days · cited-memory resolution is from the END-STATE brain (576 memories survived); ids purged mid-test are flagged `[purged]`.

## 1. Adaptive-persona timeline (3-day cumulative-return rule)

- Risk-seeking days: 45 (33 buy / 6 hold / 6 sell)
- Risk-averse days: 57 (19 buy / 10 hold / 28 sell)
- Mode switches: 26 · reasoning text explicitly echoed a risk stance on 85/102 days
- Risk-averse hit-rate: on 57 averse days with a known outcome, the agent was flat/short into 31 next-day losses — avoided (already flat) 21, caught long 10.

**Mode-switch examples (verbatim reasoning):**

- **2026-01-08** → *averse* (seeking→averse; 3-day move into 2026-01-08: -3.7%; decision **buy**, next-day -2.0%):
  > The stock has a positive cumulative return over the past 7 days indicating upward momentum. Long-term and mid-term fundamentals are strong with significant revenue growth, trading volume increase, and optimistic Bitcoin price forecasts. Positive short-term news includes institutional interest and new product developments, though there are some cautionary signals such as market volatility. The investor is risk-averse 

- **2026-02-10** → *seeking* (averse→seeking; 3-day move into 2026-02-10: +11.2%; decision **hold**, next-day -5.7%):
  > Despite positive long-term and mid-term fundamentals and being a risk-seeking investor with positive cumulative return influencing to favor positive information, the recent momentum shows a negative cumulative return over the past 7 days. Short-term information shows mixed to slightly negative sentiments, and the stock price has shown volatility and some declines triggered by broader crypto market contraction and reg

- **2026-02-13** → *seeking* (averse→seeking; 3-day move into 2026-02-13: +1.1%; decision **sell**, next-day +1.0%):
  > Despite strong long-term and mid-term fundamentals, the cumulative 7-day return and momentum are negative. Short-term negative news sentiment and volatility are significantly impacting the stock price. As a risk-seeking investor, positive information has less influence due to the negative momentum and short-term adverse conditions, indicating a sell decision.

- **2026-02-25** → *seeking* (averse→seeking; 3-day move into 2026-02-25: +7.3%; decision **buy**, next-day -1.6%):
  > The cumulative 7-day return is positive, indicating positive price momentum. Despite some short-term negative sentiment, mid-term and long-term information point to strong revenue growth, expanding product offerings, institutional interest, and optimistic Bitcoin price forecasts. Reflection-term information corroborates a positive price movement driven by solid fundamentals and market optimism. Given the risk-seeking

## 2. What the model leaned on (pivotal days)


### 2026-01-08 — averse, decision **buy**, next-day -2.0% (contrib -2.0)
- `short` id 599 `[purged]`
- `mid` id 471 `[purged]`
- `long` id 378 `[purged]`
- `reflection` id 570 (2025-11-25): The trader anticipates a positive price movement for COIN driven by strong long-term and mid-term fundamentals such as significant revenue and trading volume growth, solid liquidity, and optimistic Bitcoin price forecasts. This optimism is 
_(3/4 cited ids purged before end-state)_

### 2026-01-13 — seeking, decision **buy**, next-day +1.3% (contrib +1.3)
- `short` id 611 `[purged]`
- `short` id 635 `[purged]`
- `reflection` id 725 (2026-01-26): Despite short-term negative sentiment and a negative 7-day cumulative return, the risk-seeking profile of the investor and strong mid-term and long-term fundamentals such as significant revenue growth, expanding product offerings, instituti
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
- `mid` id 471 `[purged]`
- `mid` id 686 `[purged]`
_(6/9 cited ids purged before end-state)_

### 2026-01-15 — averse, decision **hold**, next-day +0.8% (contrib +0.0)
- `reflection` id 725 (2026-01-26): Despite short-term negative sentiment and a negative 7-day cumulative return, the risk-seeking profile of the investor and strong mid-term and long-term fundamentals such as significant revenue growth, expanding product offerings, instituti
- `reflection` id 744 (2026-02-23): Despite some negative short-term news sentiment and market volatility, the stock has shown positive momentum with a positive cumulative return over the past 7 days. Strong mid-term and long-term fundamentals such as significant revenue grow
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
- `mid` id 471 `[purged]`
- `long` id 256 (2025-08-25, negative (p=1.00/neu=1.30/neg=8.44)): Personal finance expert Suze Orman listed Coinbase Global (COIN) among her top stock picks, alongside Microsoft, Meta, Broadcom, Palantir, Apple, AMD, IonQ, and GE Vernova. Orman expressed a bullish outlook for the S&P 500, predicting it co
- `long` id 378 `[purged]`
_(2/7 cited ids purged before end-state)_

### 2026-02-10 — seeking, decision **hold**, next-day -5.7% (contrib -0.0)
- `short` id 813 `[purged]`
- `short` id 824 `[purged]`
- `reflection` id 744 (2026-02-23): Despite some negative short-term news sentiment and market volatility, the stock has shown positive momentum with a positive cumulative return over the past 7 days. Strong mid-term and long-term fundamentals such as significant revenue grow
- `reflection` id 729 (2026-01-30): Despite strong long-term and mid-term fundamentals and optimistic reflection-term outlooks, the negative cumulative return over the past 7 days and substantial negative sentiments in short-term and mid-term news, including recent falls due 
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
- `long` id 256 (2025-08-25, negative (p=1.00/neu=1.30/neg=8.44)): Personal finance expert Suze Orman listed Coinbase Global (COIN) among her top stock picks, alongside Microsoft, Meta, Broadcom, Palantir, Apple, AMD, IonQ, and GE Vernova. Orman expressed a bullish outlook for the S&P 500, predicting it co
_(5/10 cited ids purged before end-state)_

### 2026-02-11 — averse, decision **sell**, next-day -7.9% (contrib +7.9)
- `reflection` id 804 (2026-05-19): Despite strong mid-term, long-term, and reflection-term fundamentals suggesting potential positive price movement, the momentum based on the past 7 days cumulative return is negative. As a risk-averse investor facing negative cumulative ret
- `short` id 813 `[purged]`
- `short` id 822 `[purged]`
- `mid` id 553 `[purged]`
- `mid` id 559 `[purged]`
- `reflection` id 729 (2026-01-30): Despite strong long-term and mid-term fundamentals and optimistic reflection-term outlooks, the negative cumulative return over the past 7 days and substantial negative sentiments in short-term and mid-term news, including recent falls due 
_(6/9 cited ids purged before end-state)_

### 2026-02-24 — averse, decision **buy**, next-day +13.5% (contrib +13.5)
- `reflection` id 790 (2026-04-29): Although the mid-term and long-term fundamentals are generally strong and positive reflection-term information suggests a bullish outlook, the cumulative return over the past 7 days is negative, indicating negative momentum. Being a risk-av
- `short` id 824 `[purged]`
- `mid` id 872 (2026-02-20, neutral (p=1.00/neu=3.60/neg=3.12)): Coinbase Global (NASDAQ: COIN) shows bullish sentiment among options traders, with 37% of 35 detected trades being bullish and 34% bearish. Total volume is 7,608 with an average open interest of 1847.28. The stock is trading at $164.55, up 
- `reflection` id 744 (2026-02-23): Despite some negative short-term news sentiment and market volatility, the stock has shown positive momentum with a positive cumulative return over the past 7 days. Strong mid-term and long-term fundamentals such as significant revenue grow
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
- `long` id 256 (2025-08-25, negative (p=1.00/neu=1.30/neg=8.44)): Personal finance expert Suze Orman listed Coinbase Global (COIN) among her top stock picks, alongside Microsoft, Meta, Broadcom, Palantir, Apple, AMD, IonQ, and GE Vernova. Orman expressed a bullish outlook for the S&P 500, predicting it co
_(1/8 cited ids purged before end-state)_

### 2026-03-03 — seeking, decision **buy**, next-day +14.6% (contrib +14.6)
- `mid` id 890 (2026-02-26, neutral (p=1.00/neu=7.22/neg=5.92)): Coinbase Global (NASDAQ: COIN) shares rose 13.57% to $184.07 on Wednesday following a 5% increase in Bitcoin price to over $68,000. Analysts maintain a Buy rating with an average price target of $290.68, though recent moves by Goldman Sachs
- `mid` id 893 (2026-02-27, positive (p=0.99/neu=0.01/neg=0.00)): Coinbase Global (NASDAQ: COIN) shares rose as Bitcoin reclaimed $68,500. The Clarity Act is identified as a major regulatory catalyst for the company, which generated approximately $1.3 billion in stablecoin-related revenue in 2025. The fin
- `mid` id 872 (2026-02-20, neutral (p=1.00/neu=3.60/neg=3.12)): Coinbase Global (NASDAQ: COIN) shows bullish sentiment among options traders, with 37% of 35 detected trades being bullish and 34% bearish. Total volume is 7,608 with an average open interest of 1847.28. The stock is trading at $164.55, up 
- `mid` id 513 `[purged]`
- `reflection` id 744 (2026-02-23): Despite some negative short-term news sentiment and market volatility, the stock has shown positive momentum with a positive cumulative return over the past 7 days. Strong mid-term and long-term fundamentals such as significant revenue grow
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
_(1/9 cited ids purged before end-state)_

### 2026-03-23 — averse, decision **buy**, next-day -9.8% (contrib -9.8)
- `short` id 884 `[purged]`
- `short` id 894 `[purged]`
- `mid` id 872 (2026-02-20, neutral (p=1.00/neu=3.60/neg=3.12)): Coinbase Global (NASDAQ: COIN) shows bullish sentiment among options traders, with 37% of 35 detected trades being bullish and 34% bearish. Total volume is 7,608 with an average open interest of 1847.28. The stock is trading at $164.55, up 
- `mid` id 893 (2026-02-27, positive (p=0.99/neu=0.01/neg=0.00)): Coinbase Global (NASDAQ: COIN) shares rose as Bitcoin reclaimed $68,500. The Clarity Act is identified as a major regulatory catalyst for the company, which generated approximately $1.3 billion in stablecoin-related revenue in 2025. The fin
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
- `long` id 256 (2025-08-25, negative (p=1.00/neu=1.30/neg=8.44)): Personal finance expert Suze Orman listed Coinbase Global (COIN) among her top stock picks, alongside Microsoft, Meta, Broadcom, Palantir, Apple, AMD, IonQ, and GE Vernova. Orman expressed a bullish outlook for the S&P 500, predicting it co
_(2/8 cited ids purged before end-state)_

### 2026-03-30 — averse, decision **sell**, next-day +8.6% (contrib -8.6)
- `short` id 934 `[purged]`
- `mid` id 666 `[purged]`
- `mid` id 893 (2026-02-27, positive (p=0.99/neu=0.01/neg=0.00)): Coinbase Global (NASDAQ: COIN) shares rose as Bitcoin reclaimed $68,500. The Clarity Act is identified as a major regulatory catalyst for the company, which generated approximately $1.3 billion in stablecoin-related revenue in 2025. The fin
- `long` id 252 (2025-08-22, negative (p=1.00/neu=3.56/neg=8.58)): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over $50 billion, gaining 4.54%.
- `long` id 904 (2026-03-04, neutral (p=1.00/neu=2.63/neg=1.26)): Bitcoin surpassed $70,000 on Wednesday, trading at $70,906.31, which triggered a rally in crypto-related stocks. Coinbase Global Inc (NASDAQ: COIN) saw its shares rise 4.87% in premarket trading to $191.25, following a previous close of $18
- `reflection` id 718 (2026-01-14): The cumulative return of COIN over the past 7 days is positive, reflecting positive momentum. Mid-term and long-term fundamentals such as strong revenue growth, expanding product offerings, increasing institutional interest, and optimistic 
_(2/6 cited ids purged before end-state)_

### 2026-05-14 — averse, decision **buy**, next-day -7.8% (contrib -7.8)
- `short` id 1052 (2026-05-05, positive (p=0.90/neu=0.10/neg=0.00)): Coinbase (COIN) announced a 14% workforce reduction (approx. 700 employees) as part of an AI-focused restructuring plan, with most layoffs expected in Q2 2026. Restructuring costs are estimated between $50 million and $60 million. Analysts 
- `short` id 1055 `[purged]`
- `short` id 1067 `[purged]`
- `mid` id 872 (2026-02-20, neutral (p=1.00/neu=3.60/neg=3.12)): Coinbase Global (NASDAQ: COIN) shows bullish sentiment among options traders, with 37% of 35 detected trades being bullish and 34% bearish. Total volume is 7,608 with an average open interest of 1847.28. The stock is trading at $164.55, up 
- `mid` id 893 (2026-02-27, positive (p=0.99/neu=0.01/neg=0.00)): Coinbase Global (NASDAQ: COIN) shares rose as Bitcoin reclaimed $68,500. The Clarity Act is identified as a major regulatory catalyst for the company, which generated approximately $1.3 billion in stablecoin-related revenue in 2025. The fin
- `mid` id 1002 (2026-04-15, neutral (p=1.00/neu=4.11/neg=1.48)): Coinbase Global Inc. (COIN) shares rose 6.77% to $186.35 on Tuesday, supported by a 4.74% increase in the total crypto market cap. Bitcoin climbed 5.19% to near $75,526, and Ethereum gained 7.13%. Short interest in Coinbase increased to 24.
_(2/10 cited ids purged before end-state)_

## 3. Extended reflections that reached deep memory

122 extended-reflection insights survived in deep/reflection layers; 1 were later retrieved AND cited in a subsequent decision.

- **2025-07-02** (id 14, confidence high):
  > Relying heavily on long-term and mid-term fundamental indicators such as revenue growth and trading volume has generally aligned with positive next-day returns, suggesting these factors remain strong predictors of near-term performance for COIN. However, the absence of any recent trade decisions despite favorable fundamentals may indicate missed opportunitie

- **2025-07-03** (id 19, confidence high):
  > Relying on strong long-term and mid-term fundamentals such as revenue and trading volume growth has consistently aligned with positive next-day returns, indicating that fundamental analysis remains a reliable approach for COIN trading decisions. However, the magnitude of returns varies, suggesting that while fundamentals provide a solid baseline, incorporati

- **2025-07-07** (id 21, confidence high):
  > Relying solely on strong long-term and mid-term fundamentals driven by revenue and trading volume growth appears to align with modest positive next-day returns for COIN. However, the incremental gains after initial large moves suggest that fundamental strength is necessary but may not be sufficient for maximizing returns, indicating a need to integrate addit

- **2025-07-08** (id 28, confidence high):
  > Relying solely on strong long-term and mid-term fundamentals for COIN, such as significant revenue and trading volume growth, appears insufficient to consistently predict short-term next-day returns. Short-term market fluctuations and conditions may override these fundamentals, suggesting a need to integrate more short-term market indicators or technical ana

- **2025-07-09** (id 31, confidence high):
  > Relying predominantly on strong long-term and mid-term fundamentals and positive market outlooks for COIN generally correlates with positive next-day returns, but this approach occasionally fails to account for short-term market fluctuations that can result in negative returns. Incorporating short-term market signals in conjunction with fundamental analysis 

## 4. Memory-reliance profile

Citation share by layer: short 27%, mid 25%, long 28%, reflection 18% (n=967 citations).
Most-cited memory: id 252 cited 66× — `long` (2025-08-22): Following Federal Reserve Chair Jerome Powell's dovish speech at Jackson Hole, Coinbase Global Inc. (NASDAQ: COIN) was identified as one of the top-performing U.S.-listed stocks with a market cap over

## 5. Notable failures


- **2026-03-23** — bought into a >3% next-day drop while citing negative-sentiment news (next-day -9.8%):
  > The cumulative return over the past 7 days is positive, indicating positive momentum. Despite short-term volatility and mixed to negative news, the mid-term and long-term fundamentals of Coinbase (COIN) remain strong, driven by revenue growth, expanding product offerings, institutional interest, and

- **2026-05-14** — bought into a >3% next-day drop while citing negative-sentiment news (next-day -7.8%):
  > The cumulative return over the past 7 days is positive, indicating positive momentum. Despite some short-term volatility and mixed to negative news, the mid-term and long-term fundamentals of Coinbase remain strong, driven by significant revenue growth, expanding product offerings, increasing instit

- **2026-04-20** — bought into a >3% next-day drop while citing negative-sentiment news (next-day -7.4%):
  > The cumulative return over the past 7 days is positive, indicating positive momentum. Despite some short-term volatility and mixed to negative news in the short term, the mid-term and long-term fundamentals of Coinbase (COIN) remain strong, driven by significant revenue growth, expanding product off
