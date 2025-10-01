#!/usr/bin/env python3
"""
Performance Profiler для Vinted бота
Измеряет задержки на каждом этапе обработки
"""
import time
from datetime import datetime, timezone, timedelta
from logger import get_logger

logger = get_logger(__name__)

class PerformanceProfiler:
    """Профилировщик производительности с детальными метриками"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.total_stats = {
            'cycle_start_to_api_request': [],
            'api_request_to_response': [],
            'response_parsing': [],
            'db_check_time': [],
            'db_insert_time': [],
            'item_published_to_found': [],  # timestamp вещи до found_at
            'total_latency': []  # От публикации до добавления в БД
        }
    
    def start_timer(self, name):
        """Начать измерение"""
        self.start_times[name] = time.time()
        logger.info(f"[PERF] ⏱️ START: {name}")
    
    def end_timer(self, name):
        """Закончить измерение и вернуть время"""
        if name not in self.start_times:
            logger.warning(f"[PERF] ⚠️ Timer {name} was not started")
            return 0
        
        elapsed = time.time() - self.start_times[name]
        self.metrics[name] = elapsed
        logger.info(f"[PERF] ⏹️ END: {name} = {elapsed:.3f}s ({elapsed*1000:.0f}ms)")
        del self.start_times[name]
        return elapsed
    
    def record_metric(self, name, value):
        """Записать метрику напрямую"""
        self.metrics[name] = value
        logger.info(f"[PERF] 📊 METRIC: {name} = {value:.3f}s ({value*1000:.0f}ms)")
    
    def calculate_item_latency(self, item_timestamp, found_at):
        """Вычислить задержку от публикации вещи до обнаружения ботом"""
        try:
            latency = found_at - item_timestamp
            self.total_stats['item_published_to_found'].append(latency)
            logger.info(f"[PERF] 🎯 Item latency: {latency:.3f}s ({latency*1000:.0f}ms)")
            return latency
        except:
            return 0
    
    def add_to_stats(self, category, value):
        """Добавить значение в статистику"""
        if category in self.total_stats:
            self.total_stats[category].append(value)
    
    def get_summary(self):
        """Получить сводку по производительности"""
        summary = {
            'current_metrics': self.metrics.copy(),
            'statistics': {}
        }
        
        for category, values in self.total_stats.items():
            if values:
                summary['statistics'][category] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values),
                    'total': sum(values)
                }
        
        return summary
    
    def log_summary(self):
        """Вывести сводку в лог"""
        summary = self.get_summary()
        
        logger.info("=" * 80)
        logger.info("📊 PERFORMANCE SUMMARY")
        logger.info("=" * 80)
        
        if summary['current_metrics']:
            logger.info("\n🔹 Current Cycle Metrics:")
            for name, value in summary['current_metrics'].items():
                logger.info(f"  {name:40} {value:8.3f}s ({value*1000:8.0f}ms)")
        
        if summary['statistics']:
            logger.info("\n🔹 Overall Statistics:")
            for category, stats in summary['statistics'].items():
                logger.info(f"\n  {category}:")
                logger.info(f"    Min: {stats['min']:.3f}s ({stats['min']*1000:.0f}ms)")
                logger.info(f"    Avg: {stats['avg']:.3f}s ({stats['avg']*1000:.0f}ms)")
                logger.info(f"    Max: {stats['max']:.3f}s ({stats['max']*1000:.0f}ms)")
                logger.info(f"    Count: {stats['count']} samples")
        
        logger.info("=" * 80)
        
        return summary
    
    def reset_current(self):
        """Сбросить текущие метрики (для нового цикла)"""
        self.metrics = {}
        self.start_times = {}

# Глобальный экземпляр профилировщика
profiler = PerformanceProfiler()

def get_profiler():
    """Получить глобальный профилировщик"""
    return profiler

