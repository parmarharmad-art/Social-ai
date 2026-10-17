def make_script(topic,duration=30,language="Hindi"):
 topic=topic.strip()
 if not topic: raise ValueError("Topic is required")
 if language=="Hinglish":
  return f"Ek useful AI workflow dekhiye: {topic}. Pehle input ko ek jagah collect karein, phir AI se draft ya classification karayein, aur final output ko review ke baad hi use karein. AI output ko verify karna zaroori hai aur workflow ko apne tools ke saath test karein. Aap kaunsa task automate karna chahte hain? Practical AI workflows ke liye Kiran Kumar ko follow karein."
 return f"क्या आप {topic} को आसान बनाना चाहते हैं? पहले ज़रूरी जानकारी एक जगह इकट्ठा करें, फिर AI से शुरुआती ड्राफ्ट या वर्गीकरण करवाएँ। इसके बाद परिणाम को खुद जाँचें और सही होने पर ही इस्तेमाल करें। AI की हर बात सही नहीं होती, इसलिए workflow को अपने tools के साथ test करें। आप कौन-सा काम automate करना चाहते हैं? ऐसे practical AI workflows के लिए Kiran Kumar को follow करें।"
def make_caption(topic,script):
 return f"{topic}\n\nइस workflow को इस्तेमाल करने से पहले अपने tools और output को verify करें।\n\nआप कौन-सा काम automate करना चाहते हैं? Comment में बताइए।\n\nFollow @officialkiraankumar for practical AI workflows.\n\n#AIAutomation #HindiTech #AIWorkflows #DigitalMarketing #KiranKumar"
