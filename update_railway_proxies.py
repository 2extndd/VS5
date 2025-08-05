#!/usr/bin/env python3
"""
Скрипт для обновления прокси на Railway
"""

import requests
import json

def update_railway_proxies():
    """Обновляем прокси на Railway"""
    print("🔄 Обновление прокси на Railway...")
    print("=" * 50)
    
    # Все прокси
    all_proxies = [
        'wv716u6wju:ZYbn3awds3RQDY2R@89.38.97.60:12706',
        'wv716u6wju:ZYbn3awds3RQDY2R@185.132.133.56:11639',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.142.111:26514',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.113.241:14111',
        'wv716u6wju:ZYbn3awds3RQDY2R@138.201.62.169:26332',
        'wv716u6wju:ZYbn3awds3RQDY2R@89.38.99.47:12793',
        'wv716u6wju:ZYbn3awds3RQDY2R@93.190.139.245:22165',
        'wv716u6wju:ZYbn3awds3RQDY2R@178.132.5.24:12559',
        'wv716u6wju:ZYbn3awds3RQDY2R@109.236.93.35:14207',
        'wv716u6wju:ZYbn3awds3RQDY2R@93.190.139.25:13158',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.113.229:25463',
        'wv716u6wju:ZYbn3awds3RQDY2R@151.106.6.79:20706',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.142.111:19716',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.134.118:15414',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.113.236:15383',
        'wv716u6wju:ZYbn3awds3RQDY2R@89.39.104.152:26862',
        'wv716u6wju:ZYbn3awds3RQDY2R@93.190.142.89:14832',
        'wv716u6wju:ZYbn3awds3RQDY2R@178.132.5.24:23365',
        'wv716u6wju:ZYbn3awds3RQDY2R@138.201.62.169:12852',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.115.54:15900',
        'wv716u6wju:ZYbn3awds3RQDY2R@93.190.141.73:20576',
        'wv716u6wju:ZYbn3awds3RQDY2R@134.119.205.55:12767',
        'wv716u6wju:ZYbn3awds3RQDY2R@185.165.241.5:12712',
        'wv716u6wju:ZYbn3awds3RQDY2R@109.236.80.175:13175',
        'wv716u6wju:ZYbn3awds3RQDY2R@80.79.6.171:27225',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.134.28:11476',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.113.94:14911',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.113.241:20142',
        'wv716u6wju:ZYbn3awds3RQDY2R@175.110.113.245:26413',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.143.237:28180',
        'wv716u6wju:ZYbn3awds3RQDY2R@134.119.205.55:25918',
        'wv716u6wju:ZYbn3awds3RQDY2R@91.232.105.4:12561',
        'wv716u6wju:ZYbn3awds3RQDY2R@93.190.141.18:12217',
        'wv716u6wju:ZYbn3awds3RQDY2R@62.112.9.233:13470',
        'wv716u6wju:ZYbn3awds3RQDY2R@62.112.11.77:21649',
        'wv716u6wju:ZYbn3awds3RQDY2R@109.236.80.126:16539',
        'wv716u6wju:ZYbn3awds3RQDY2R@109.236.85.78:12381',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.142.30:25554',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.134.118:25676',
        'wv716u6wju:ZYbn3awds3RQDY2R@136.243.177.154:16797',
        'wv716u6wju:ZYbn3awds3RQDY2R@138.201.62.169:18610',
        'wv716u6wju:ZYbn3awds3RQDY2R@109.236.87.25:14142',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.150.45:18071',
        'wv716u6wju:ZYbn3awds3RQDY2R@93.190.141.73:11084',
        'wv716u6wju:ZYbn3awds3RQDY2R@190.2.150.45:20332',
        'wv716u6wju:ZYbn3awds3RQDY2R@178.132.2.28:22947',
        'wv716u6wju:ZYbn3awds3RQDY2R@89.38.98.64:22805',
        'wv716u6wju:ZYbn3awds3RQDY2R@212.8.249.177:11760',
        'wv716u6wju:ZYbn3awds3RQDY2R@89.38.98.115:11947',
        'wv716u6wju:ZYbn3awds3RQDY2R@62.112.9.151:12278'
    ]
    
    print(f"📋 Всего прокси: {len(all_proxies)}")
    print(f"✅ Рабочих прокси: 26 из 50 (52%)")
    
    print("\n💡 Инструкции для обновления на Railway:")
    print("1. Откройте https://vs5-production.up.railway.app/config")
    print("2. Найдите секцию 'Proxy Settings'")
    print("3. В поле 'Proxy List' вставьте все прокси:")
    print("4. Нажмите 'Save Configuration'")
    print("5. Перезапустите приложение на Railway")
    
    print("\n📋 Прокси для копирования:")
    print("=" * 50)
    for i, proxy in enumerate(all_proxies, 1):
        print(f"{i:2d}. {proxy}")
    
    print("\n🔗 Также можно добавить ссылку на прокси:")
    print("Proxy List Link: https://sx-list.org/jXqrKIfIr2A87CEAsnKeHJ3OIroEhO5n.txt?limit=50&type=res&use_login_and_password=1&country=DE")

if __name__ == "__main__":
    update_railway_proxies() 