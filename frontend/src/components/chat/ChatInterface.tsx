import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Mic,
  MicOff,
  Compass,
  Sparkles,
  Bot,
  User as UserIcon,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  HelpCircle,
  Clock,
  Layers,
  MapPin,
  Anchor,
  Wind,
  Waves,
  Globe,
  ChevronDown,
} from 'lucide-react';
import { useAppState } from '../../hooks/useAppState';
import { appStore } from '../../stores/appState';
import { chatService } from '../../services/chat/chatService';
import { AgentActivityPanel } from '../agents/AgentActivityPanel';
import { getTranslation, SUPPORTED_LANGUAGES, LanguageCode } from '../../i18n/translations';
import { ChatMessage, OrcaQueryResponse } from '../../types';

interface ChatInterfaceProps {
  onSyncMapToCoords?: (lat: number, lon: number, route?: [number, number][]) => void;
  initialQuery?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  onSyncMapToCoords,
  initialQuery,
}) => {
  const {
    language,
    userLocation,
    activeAgents,
    isAgentRunning,
    activeQueryStatusMessage,
    user,
  } = useAppState();

  const t = (key: string) => getTranslation(language, key);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize Speech Recognition if supported in browser
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;

      // Map app language to BCP 47 language tag
      const langMap: Record<string, string> = {
        en: 'en-IN',
        hi: 'hi-IN',
        hinglish: 'hi-IN',
        mr: 'mr-IN',
        ta: 'ta-IN',
        te: 'te-IN',
        bn: 'bn-IN',
        gu: 'gu-IN',
        kn: 'kn-IN',
        ml: 'ml-IN',
        pa: 'pa-IN',
        or: 'or-IN',
        ur: 'ur-IN',
      };
      recognition.lang = langMap[language] || 'en-IN';

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, [language]);

  const toggleSpeech = () => {
    if (!speechSupported || !recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (e) {
        console.error('Speech recognition error:', e);
      }
    }
  };

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isAgentRunning]);

  // Handle programmatic initial query (e.g. from Home page quick actions)
  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      handleSend(initialQuery);
    }
  }, [initialQuery]);

  const handleSend = async (queryToSend?: string) => {
    const query = (queryToSend || inputText).trim();
    if (!query || isAgentRunning) return;

    setInputText('');
    setErrorMessage(null);

    const userMsgId = 'user-' + Date.now();
    const newUserMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, newUserMsg]);
    appStore.setAgentRunning(true, 'Query accepted. Routing to Planner Agent...');

    try {
      // Build location payload from active user location
      const locationPayload = userLocation
        ? {
            name: userLocation.name || 'Coastal Point',
            latitude: userLocation.latitude,
            longitude: userLocation.longitude,
          }
        : undefined;

      // Submit to backend
      const response: OrcaQueryResponse = await chatService.submitQuery({
        query,
        location: locationPayload,
        userProfile: {
          role: user?.role || 'fisherman',
          vesselClass: user?.vesselClass || 'motorized_fiberglass',
          language,
        },
      });

      const assistantMsgId = 'assistant-' + Date.now();
      const newAssistantMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: response.answer || 'NEERDRISTI reasoning complete.',
        timestamp: new Date().toISOString(),
        orcaResponse: response,
      };

      setMessages((prev) => [...prev, newAssistantMsg]);
      appStore.setAgentRunning(false, 'Analysis Complete');

      // Synchronize Map: if location/evidence or route was returned, fly to coordinates!
      if (userLocation && onSyncMapToCoords) {
        onSyncMapToCoords(userLocation.latitude, userLocation.longitude);
      }
    } catch (err: any) {
      console.error('Error submitting query to NEERDRISTI:', err);
      appStore.setAgentRunning(false, null);
      setErrorMessage(
        'NEERDRISTI could not complete the multi-agent analysis at this time. Please check your network and try again.'
      );
    }
  };

  const [chatLangMenuOpen, setChatLangMenuOpen] = useState(false);

  const getLocalizedQuickActions = (lang: string) => {
    switch (lang) {
      case 'hi':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'मेरे स्थान के पास मछली पकड़ने के संभावित क्षेत्र (PFZ) खोजें और समुद्र की स्थिति बताएं।' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'आज समुद्र में लहरों की ऊंचाई, हवा और बहाव कैसा है? क्या समुद्र में जाना सुरक्षित है?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'कल सुबह मछली पकड़ने के लिए जाना सुरक्षित रहेगा क्या? मौसम और जोखिम का विश्लेषण करें।' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'तटीय मौसम का पूर्वानुमान और चक्रवात चेतावनी की स्थिति बताएं।' },
        ];
      case 'hinglish':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'Mere paas fishing ke liye safe potential fishing zone (PFZ) batao aur sea conditions check karo.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'Aaj samundar mein wave height, swell aur currents kaisa hai? Fishing safe hai?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'Kal subah fishing ke liye nikalna safe rahega kya? Weather aur risk check karo.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'Coastal weather forecast aur cyclone alert status check karo.' },
        ];
      case 'mr':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'माझ्या स्थानाजवळील संभाव्य मासेमारी क्षेत्रे (PFZ) शोधा आणि समुद्राची परिस्थिती तपासा.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'आज समुद्रातील लाटांची उंची, वारा आणि प्रवाह कसा आहे? समुद्रात जाणे सुरक्षित आहे का?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'उद्या सकाळी मासेमारीसाठी जाणे सुरक्षित राहील का? हवामान आणि धोक्यांचे विश्लेषण करा.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'किनारपट्टीचे हवामान अंदाज आणि चक्रीवादळ इशारा स्थिती तपासा.' },
        ];
      case 'ta':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'எனது இருப்பிடத்திற்கு அருகிலுள்ள சாத்தியமான மீன்பிடி மண்டலங்களை (PFZ) கண்டறிந்து கடல் நிலையை சரிபார்க்கவும்.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'இன்று கடலில் அலைகளின் உயரம், காற்று மற்றும் நீரோட்டம் எப்படி உள்ளது? மீன்பிடிக்க செல்வது பாதுகாப்பானதா?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'நாளை காலை மீன்பிடிக்க செல்வது பாதுகாப்பானதா? வானிலை மற்றும் ஆபத்துகளை மதிப்பிடவும்.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'கடலோர வானிலை முன்னறிவிப்பு மற்றும் புயல் எச்சரிக்கை நிலையை காட்டவும்.' },
        ];
      case 'te':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'నా స్థానానికి సమీపంలో సంభావ్య చేపల వేట మండలాలను (PFZ) కనుగొని సముద్ర పరిస్థితులను తనిఖీ చేయండి.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'ఈ రోజు సముద్రంలో అలల ఎత్తు, గాలి వేగం ఎలా ఉంది? సముద్రంలోకి వెళ్లడం సురక్షితమేనా?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'రేపు ఉదయం చేపల వేటకు వెళ్లడం సురక్షితమేనా? వాతావరణం మరియు ప్రమాదాలను విశ్లేషించండి.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'తీరప్రాంత వాతావరణ సూచన మరియు తుఫాను హెచ్చరిక స్థితిని చూపించండి.' },
        ];
      case 'bn':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'আমার অবস্থানের কাছাকাছি সম্ভাব্য মৎস্য আহরণ ক্ষেত্র (PFZ) খুঁজুন এবং সমুদ্রের অবস্থা মূল্যায়ন করুন।' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'আজ সমুদ্রে ঢেউয়ের উচ্চতা, বাতাস এবং সমুদ্রের অবস্থা কেমন? মাছ ধরা কি নিরাপদ?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'কাল সকালে মাছ ধরতে যাওয়া কি নিরাপদ হবে? আবহাওয়া এবং ঝুঁকির কারণগুলি মূল্যায়ন করুন।' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'উপকূলীয় আবহাওয়ার পূর্বাভাস এবং সক্রিয় ঘূর্ণিঝড় সতর্কতা প্রদর্শন করুন।' },
        ];
      case 'gu':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'મારા સ્થાન નજીક સંભવિત માછીમારી વિસ્તારો (PFZ) શોધો અને દરિયાઈ અનુકૂળતા તપાસો.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'આજે દરિયામાં મોજાની ઊંચાઈ, પવન અને પ્રવાહ કેવો છે? માછીમારી માટે જવું સલામત છે?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'આવતીકાલે સવારે માછીમારી માટે જવું સુરક્ષિત રહેશે? જોખમી પરિબળો તપાસો.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'દરિયાકાંઠાના હવામાનની આગાહી અને વાવાઝોડાની ચેતવણી દર્શાવો.' },
        ];
      case 'kn':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'ನನ್ನ ಸ್ಥಳದ ಸಮೀಪವಿರುವ ಸಂಭಾವ್ಯ ಮೀನುಗಾರಿಕಾ ವಲಯಗಳನ್ನು (PFZ) ಹುಡುಕಿ ಮತ್ತು ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಯನ್ನು ಪರಿಶೀಲಿಸಿ.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'ಇಂದು ಸಮುದ್ರದಲ್ಲಿ ಅಲೆಗಳ ಎತ್ತರ, ಗಾಳಿ ಮತ್ತು ಪ್ರವಾಹ ಹೇಗಿದೆ? ಮೀನುಗಾರಿಕೆ ಸುರಕ್ಷಿತವೇ?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಮೀನುಗಾರಿಕೆಗೆ ಹೋಗುವುದು ಸುರಕ್ಷಿತವೇ? ಹವಾಮಾನ ಮತ್ತು ಅಪಾಯದ ಅಂಶಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'ಕರಾವಳಿ ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಸಕ್ರಿಯ ಚಂಡಮಾರುತದ ಎಚ್ಚರಿಕೆಯನ್ನು ತೋರಿಸಿ.' },
        ];
      case 'ml':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'എന്റെ ലൊക്കേഷന് സമീപമുള്ള മത്സ്യബന്ധന മേഖലകൾ (PFZ) കണ്ടെത്തുകയും കടൽ അവസ്ഥ വിലയിരുത്തുകയും ചെയ്യുക.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'ഇന്ന് കടലിലെ തിരമാലകളുടെ ഉയരവും കാറ്റും എങ്ങനെയുണ്ട്? കടലിൽ പോകുന്നത് സുരക്ഷിതമാണോ?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'നാളെ രാവിലെ മത്സ്യബന്ധനത്തിന് പോകുന്നത് സുരക്ഷിതമാണോ? അപകടസാധ്യതകൾ വിലയിരുത്തുക.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'തീരദേശ കാലാവസ്ഥാ പ്രവചനവും ചുഴലിക്കാറ്റ് മുന്നറിയിപ്പുകളും കാണിക്കുക.' },
        ];
      case 'pa':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'ਮੇਰੇ ਟਿਕਾਣੇ ਨੇੜੇ ਮੱਛੀ ਫੜਨ ਵਾਲੇ ਸੰਭਾਵੀ ਖੇਤਰ (PFZ) ਲੱਭੋ ਅਤੇ ਸਮੁੰਦਰ ਦੀ ਸਥਿਤੀ ਦੀ ਜਾਂਚ ਕਰੋ।' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'ਅੱਜ ਸਮੁੰਦਰ ਵਿੱਚ ਲਹਿਰਾਂ ਦੀ ਉਚਾਈ ਅਤੇ ਹਵਾ ਦੀ ਰਫ਼ਤਾਰ ਕਿਹੋ ਜਿਹੀ ਹੈ? ਕੀ ਸਮੁੰਦਰ ਜਾਣਾ ਸੁਰੱਖਿਅਤ ਹੈ?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'ਕੀ ਕੱਲ੍ਹ ਸਵੇਰੇ ਮੱਛੀ ਫੜਨ ਜਾਣਾ ਸੁਰੱਖਿਅਤ ਰਹੇਗਾ? ਮੌਸਮ ਅਤੇ ਖਤਰੇ ਦੇ ਕਾਰਕਾਂ ਦੀ ਜਾਂਚ ਕਰੋ।' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'ਤੱਟਵਰਤੀ ਮੌਸਮ ਦੀ ਭਵਿੱਖਬਾਣੀ ਅਤੇ ਚੱਕਰਵਾਤ ਚੇਤਾਵਨੀ ਦੀ ਸਥਿਤੀ ਦੱਸੋ।' },
        ];
      case 'or':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'ମୋ ସ୍ଥାନ ନିକଟରେ ସମ୍ଭାବ୍ୟ ମତ୍ସ୍ୟ ଧରିବା କ୍ଷେତ୍ର (PFZ) ଖୋଜ ଏବଂ ସମୁଦ୍ର ଅବସ୍ଥା ଯାଞ୍ଚ କରନ୍ତୁ।' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'ଆଜି ସମୁଦ୍ରରେ ଢେଉର ଉଚ୍ଚତା ଏବଂ ପବନର ଗତି କିପରି ଅଛି? ମାଛ ଧରିବାକୁ ଯିବା ସୁରକ୍ଷିତ କି?' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'କାଲି ସକାଳେ ମାଛ ଧରିବାକୁ ଯିବା ନିରାପଦ ହେବ କି? ପାଣିପାଗ ଏବଂ ବିପଦ କାରକ ଯାଞ୍ଚ କରନ୍ତୁ।' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'ଉପକୂଳ ପାଣିପାଗ ପୂର୍ବାନୁମାନ ଏବଂ ସକ୍ରିୟ ବାତ୍ୟା ଚେତାବନୀ ଦେଖାନ୍ତୁ।' },
        ];
      case 'ur':
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'میرے مقام کے قریب مچھلی پکڑنے کے ممکنہ زونز (PFZ) تلاش کریں اور سمندری حالات کا جائزہ لیں۔' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'آج سمندر میں لہروں کی اونچائی، ہوا کی رفتار کیسی ہے؟ کیا سمندر میں جانا محفوظ ہے؟' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'کیا کل صبح ماہی گیری کے لیے جانا محفوظ رہے گا؟ تمام خطرات کا جائزہ لیں۔' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'ساحلی موسم کی پیشن گوئی اور فعال سمندری طوفان کے الرٹس دکھائیں۔' },
        ];
      default:
        return [
          { id: 'pfz', label: t('findFishingZones'), icon: '🎣', query: 'Find potential fishing zones near my location today and evaluate sea suitability.' },
          { id: 'sea', label: t('checkSeaConditions'), icon: '🌊', query: 'Check current marine wave heights, swell, sea-state, and wind velocity near my harbor.' },
          { id: 'trip', label: t('planSafeTrip'), icon: '🛥️', query: 'Can I go out to sea tomorrow morning for fishing? Evaluate all risk factors.' },
          { id: 'weather', label: t('checkWeather'), icon: '🌦️', query: 'Show coastal meteorological weather forecast and active cyclone alerts.' },
        ];
    }
  };

  const quickActions = getLocalizedQuickActions(language);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        backgroundColor: 'var(--bg-abyss)',
      }}
    >
      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {/* Welcome Empty State */}
        {messages.length === 0 && (
          <div
            className="animate-fade-in"
            style={{
              maxWidth: '680px',
              margin: 'auto',
              width: '100%',
              padding: '1rem 0',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '68px',
                height: '68px',
                borderRadius: '18px',
                overflow: 'hidden',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.25rem',
                boxShadow: '0 0 24px rgba(6, 182, 212, 0.45)',
                border: '1.5px solid rgba(56, 189, 248, 0.4)',
                backgroundColor: '#0a1d37',
              }}
            >
              <img
                src="/neerdristi.logo.png"
                alt="NEERDRISTI Logo"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>

            <h1
              style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: '#ffffff',
                marginBottom: '0.5rem',
              }}
            >
              {t('greeting')} 👋
            </h1>
            <p
              style={{
                fontSize: '1rem',
                color: 'var(--text-muted)',
                marginBottom: '1.75rem',
              }}
            >
              {t('askPrompt')}
            </p>

            {/* Quick Actions Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '0.75rem',
                textAlign: 'left',
              }}
            >
              {quickActions.map((action) => (
                <div
                  key={action.id}
                  onClick={() => handleSend(action.query)}
                  className="glass-panel"
                  style={{
                    padding: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    border: '1px solid var(--border-subtle)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--cyan-primary)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <span style={{ fontSize: '1.4rem' }}>{action.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#ffffff' }}>
                      {action.label}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      Tap to evaluate
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Message Thread */}
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          const resp = msg.orcaResponse;

          return (
            <div
              key={msg.id}
              className="animate-fade-in"
              style={{
                display: 'flex',
                gap: '10px',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: isUser ? '85%' : '92%',
                width: isUser ? 'auto' : '100%',
              }}
            >
              {!isUser && (
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: '2px',
                    boxShadow: '0 0 10px rgba(6, 182, 212, 0.35)',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    backgroundColor: '#0a1d37',
                  }}
                >
                  <img
                    src="/neerdristi.logo.png"
                    alt="NEERDRISTI"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                </div>
              )}

              <div style={{ flex: 1 }}>
                {!isUser && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--cyan-primary)' }}>
                      NEERDRISTI Marine AI
                    </span>
                    {resp?.language && (
                      <span
                        style={{
                          fontSize: '0.62rem',
                          backgroundColor: 'rgba(6, 182, 212, 0.15)',
                          color: '#38bdf8',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          border: '1px solid rgba(6, 182, 212, 0.3)',
                          fontWeight: 600,
                        }}
                      >
                        {SUPPORTED_LANGUAGES.find((l) => l.code === resp.language)?.flag || '🇮🇳'}{' '}
                        {SUPPORTED_LANGUAGES.find((l) => l.code === resp.language)?.nativeLabel || resp.language}
                      </span>
                    )}
                  </div>
                )}

                <div
                  style={{
                    padding: '14px 18px',
                    borderRadius: isUser ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                    backgroundColor: isUser ? '#0284c7' : 'var(--bg-card)',
                    border: isUser ? 'none' : '1px solid var(--border-subtle)',
                    color: '#ffffff',
                    lineHeight: '1.55',
                    fontSize: '0.9rem',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {msg.content}
                </div>

                {/* If Assistant Message contains structured ORCA response */}
                {resp && (
                  <div style={{ marginTop: '8px' }}>
                    {/* Verdict & Risk HUD Badge */}
                    {resp.recommendation && (
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          backgroundColor:
                            resp.recommendation === 'GO'
                              ? 'var(--status-go-bg)'
                              : resp.recommendation === 'NO_GO'
                              ? 'var(--status-nogo-bg)'
                              : 'var(--status-caution-bg)',
                          border: `1px solid ${
                            resp.recommendation === 'GO'
                              ? 'rgba(16, 185, 129, 0.4)'
                              : resp.recommendation === 'NO_GO'
                              ? 'rgba(239, 68, 68, 0.4)'
                              : 'rgba(245, 158, 11, 0.4)'
                          }`,
                          marginBottom: '8px',
                          marginRight: '8px',
                        }}
                      >
                        {resp.recommendation === 'GO' ? (
                          <ShieldCheck size={16} color="var(--status-go)" />
                        ) : resp.recommendation === 'NO_GO' ? (
                          <ShieldAlert size={16} color="var(--status-nogo)" />
                        ) : (
                          <AlertTriangle size={16} color="var(--status-caution)" />
                        )}
                        <span
                          style={{
                            fontWeight: 700,
                            fontSize: '0.75rem',
                            color:
                              resp.recommendation === 'GO'
                                ? 'var(--status-go)'
                                : resp.recommendation === 'NO_GO'
                                ? 'var(--status-nogo)'
                                : 'var(--status-caution)',
                          }}
                        >
                          VERDICT: {resp.recommendation} | RISK: {resp.riskLevel} ({resp.riskScore}/100)
                        </span>
                      </div>
                    )}

                    {/* Agent Execution Trace Mini-Panel */}
                    {resp.trace?.agentStatuses && resp.trace.agentStatuses.length > 0 && (
                      <AgentActivityPanel
                        traces={resp.trace.agentStatuses}
                        isRunning={false}
                      />
                    )}

                    {/* Evidence Provenance Footer */}
                    {resp.evidence && resp.evidence.length > 0 && (
                      <div
                        style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: '6px',
                          marginTop: '6px',
                          fontSize: '0.7rem',
                          color: 'var(--text-dim)',
                        }}
                      >
                        {resp.evidence.slice(0, 3).map((item, idx) => (
                          <span
                            key={idx}
                            style={{
                              backgroundColor: 'rgba(255, 255, 255, 0.04)',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              border: '1px solid var(--border-subtle)',
                            }}
                          >
                            ✓ {item.name}: {item.sourceName} ({item.freshness})
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div
                  style={{
                    fontSize: '0.65rem',
                    color: 'var(--text-dim)',
                    marginTop: '4px',
                    textAlign: isUser ? 'right' : 'left',
                  }}
                >
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          );
        })}

        {/* Real-time Agent Multi-Agent Execution Progress Tracker */}
        {isAgentRunning && (
          <div style={{ width: '100%', maxWidth: '92%' }}>
            <AgentActivityPanel
              traces={activeAgents}
              isRunning={true}
              statusMessage={activeQueryStatusMessage}
            />
          </div>
        )}

        {errorMessage && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertTriangle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Multilingual Selector Strip */}
      <div
        style={{
          padding: '6px 1rem',
          backgroundColor: 'rgba(8, 16, 30, 0.96)',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Globe size={13} color="var(--teal-accent)" />
          <span style={{ fontWeight: 600 }}>Language:</span>
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setChatLangMenuOpen(!chatLangMenuOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '3px 8px',
                borderRadius: '6px',
                backgroundColor: 'rgba(6, 182, 212, 0.15)',
                border: '1px solid var(--border-active)',
                color: 'var(--cyan-hover)',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <span>{SUPPORTED_LANGUAGES.find((l) => l.code === language)?.flag || '🇮🇳'}</span>
              <span>{SUPPORTED_LANGUAGES.find((l) => l.code === language)?.nativeLabel || 'हिन्दी'}</span>
              <ChevronDown size={12} />
            </button>

            {chatLangMenuOpen && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: 0,
                  marginBottom: '6px',
                  width: '210px',
                  maxHeight: '260px',
                  overflowY: 'auto',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-active)',
                  borderRadius: '8px',
                  boxShadow: '0 8px 25px rgba(0,0,0,0.6)',
                  zIndex: 1010,
                  padding: '4px',
                }}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <div
                    key={l.code}
                    onClick={() => {
                      appStore.setLanguage(l.code);
                      setChatLangMenuOpen(false);
                    }}
                    style={{
                      padding: '6px 10px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: '0.78rem',
                      backgroundColor: language === l.code ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                      color: language === l.code ? 'var(--cyan-hover)' : 'var(--text-main)',
                    }}
                  >
                    <span>{l.flag} {l.nativeLabel}</span>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>{l.code.toUpperCase()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Language Switch Pills */}
        <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', maxWidth: '62%' }}>
          {[
            { code: 'hi', label: 'हिन्दी' },
            { code: 'hinglish', label: 'Hinglish' },
            { code: 'mr', label: 'मराठी' },
            { code: 'ta', label: 'தமிழ்' },
            { code: 'te', label: 'తెలుగు' },
            { code: 'bn', label: 'বাংলা' },
            { code: 'gu', label: 'ગુજરાતી' },
            { code: 'kn', label: 'ಕನ್ನಡ' },
            { code: 'ml', label: 'മലയാളം' },
            { code: 'en', label: 'EN' },
          ].map((item) => (
            <button
              key={item.code}
              onClick={() => appStore.setLanguage(item.code as LanguageCode)}
              style={{
                fontSize: '0.68rem',
                padding: '2px 7px',
                borderRadius: '4px',
                backgroundColor: language === item.code ? 'var(--cyan-primary)' : 'rgba(255,255,255,0.05)',
                color: language === item.code ? '#ffffff' : 'var(--text-dim)',
                border: language === item.code ? '1px solid var(--cyan-primary)' : '1px solid rgba(255,255,255,0.08)',
                cursor: 'pointer',
                fontWeight: language === item.code ? 700 : 500,
                whiteSpace: 'nowrap',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Bar */}
      <div
        style={{
          padding: '1rem',
          backgroundColor: 'rgba(10, 22, 38, 0.98)',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        {/* Voice Input Button */}
        {speechSupported && (
          <button
            onClick={toggleSpeech}
            className="btn-icon"
            title={isListening ? t('micListening') : 'Click to Speak'}
            style={{
              backgroundColor: isListening ? 'rgba(239, 68, 68, 0.25)' : undefined,
              borderColor: isListening ? 'var(--status-nogo)' : undefined,
              color: isListening ? 'var(--status-nogo)' : undefined,
            }}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
        )}

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSend();
          }}
          placeholder={isListening ? t('micListening') : t('inputPlaceholder')}
          style={{
            flex: 1,
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '12px 16px',
            color: '#ffffff',
            fontSize: '0.9rem',
            outline: 'none',
          }}
        />

        <button
          onClick={() => handleSend()}
          disabled={!inputText.trim() || isAgentRunning}
          className="btn-primary"
          style={{ padding: '12px 18px' }}
        >
          <Send size={16} />
          <span className="desktop-send-text">{t('send')}</span>
        </button>
      </div>

      <style>{`
        @media (max-width: 640px) {
          .desktop-send-text {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
};
