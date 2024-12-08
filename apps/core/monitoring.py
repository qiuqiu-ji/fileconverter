"""错误监控"""
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json

class ErrorMonitor:
    """错误监控"""
    
    @staticmethod
    def record_error(error_info):
        """记录错误"""
        # 更新错误计数
        cache_key = f"error_count:{timezone.now().strftime('%Y-%m-%d')}"
        try:
            cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=86400)  # 24小时
        
        # 记录错误详情
        errors_key = f"errors:{timezone.now().strftime('%Y-%m-%d')}"
        errors = cache.get(errors_key) or []
        errors.append({
            'error_id': error_info['error_id'],
            'exception': error_info['exception'],
            'url': error_info['url'],
            'timestamp': timezone.now().isoformat(),
            'count': 1
        })
        cache.set(errors_key, errors[:1000], timeout=86400)  # 保留最近1000条
    
    @staticmethod
    def get_error_stats(days=7):
        """获取错误统计"""
        stats = {
            'total_errors': 0,
            'daily_counts': [],
            'common_errors': {}
        }
        
        # 统计每日错误数
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            count = cache.get(f"error_count:{date.strftime('%Y-%m-%d')}") or 0
            stats['daily_counts'].append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
            stats['total_errors'] += count
        
        # 统计常见错误
        errors_key = f"errors:{timezone.now().strftime('%Y-%m-%d')}"
        errors = cache.get(errors_key) or []
        for error in errors:
            key = error['exception'][:100]
            if key in stats['common_errors']:
                stats['common_errors'][key]['count'] += 1
            else:
                stats['common_errors'][key] = {
                    'message': error['exception'],
                    'count': 1,
                    'last_seen': error['timestamp']
                }
        
        return stats 

    def analyze_error_patterns(self):
        """分析错误模式"""
        stats = self.get_error_stats(days=7)
        patterns = {
            'frequent_errors': [],
            'error_trends': [],
            'impact_levels': {
                'high': [],
                'medium': [],
                'low': []
            }
        }
        
        # 分析频繁错误
        for error, info in stats['common_errors'].items():
            if info['count'] > 10:
                patterns['frequent_errors'].append({
                    'error': error,
                    'count': info['count'],
                    'last_seen': info['last_seen']
                })
        
        # 分析趋势
        daily_counts = stats['daily_counts']
        if len(daily_counts) > 1:
            trend = (daily_counts[0]['count'] - daily_counts[-1]['count']) / len(daily_counts)
            patterns['error_trends'].append({
                'period': '7d',
                'trend': trend,
                'increasing': trend > 0
            })
        
        # 分析影响级别
        for error, info in stats['common_errors'].items():
            if info['count'] > 100:
                patterns['impact_levels']['high'].append(error)
            elif info['count'] > 10:
                patterns['impact_levels']['medium'].append(error)
            else:
                patterns['impact_levels']['low'].append(error)
        
        return patterns

    def generate_error_report(self, days=7):
        """生成错误报告"""
        stats = self.get_error_stats(days)
        patterns = self.analyze_error_patterns()
        
        report = {
            'summary': {
                'total_errors': stats['total_errors'],
                'unique_errors': len(stats['common_errors']),
                'period': f'{days} days',
                'generated_at': timezone.now().isoformat()
            },
            'trends': {
                'daily_counts': stats['daily_counts'],
                'patterns': patterns['error_trends']
            },
            'top_errors': sorted(
                stats['common_errors'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10],
            'impact_analysis': patterns['impact_levels'],
            'recommendations': self._generate_recommendations(patterns)
        }
        
        return report

    def _generate_recommendations(self, patterns):
        """生成建议"""
        recommendations = []
        
        # 基于频繁错误的建议
        if patterns['frequent_errors']:
            recommendations.append({
                'type': 'high_frequency',
                'message': f"Found {len(patterns['frequent_errors'])} frequently occurring errors",
                'action': "Investigate and fix the root cause of these errors"
            })
        
        # 基于趋势的建议
        for trend in patterns['error_trends']:
            if trend['increasing']:
                recommendations.append({
                    'type': 'increasing_trend',
                    'message': f"Error rate is increasing over the past {trend['period']}",
                    'action': "Review recent changes and monitor system resources"
                })
        
        # 基于影响级别的建议
        if patterns['impact_levels']['high']:
            recommendations.append({
                'type': 'high_impact',
                'message': f"Found {len(patterns['impact_levels']['high'])} high-impact errors",
                'action': "Prioritize fixing these errors to improve system stability"
            })
        
        return recommendations

    def get_real_time_metrics(self):
        """获取实时指标"""
        from django.core.cache import cache
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        metrics = {
            'current': {
                'error_count': 0,
                'error_rate': 0,
                'response_time': 0,
            },
            'trends': {
                'last_hour': [],
                'error_rate_change': 0,
            },
            'alerts': [],
            'system_health': {
                'cpu': 0,
                'memory': 0,
                'disk': 0,
            }
        }
        
        # 获取最近一小时的错误数
        hour_errors = []
        for minute in range(60):
            time_key = (now - timedelta(minutes=minute)).strftime('%Y%m%d%H%M')
            count = cache.get(f'error_count:{time_key}', 0)
            hour_errors.append(count)
            if minute < 5:  # 最近5分钟
                metrics['current']['error_count'] += count
        
        # 计算错误率变化
        if len(hour_errors) >= 2:
            current_rate = sum(hour_errors[:5]) / 5
            previous_rate = sum(hour_errors[-5:]) / 5
            metrics['trends']['error_rate_change'] = (
                (current_rate - previous_rate) / previous_rate * 100 
                if previous_rate > 0 else 0
            )
        
        # 获取系统健康状态
        try:
            import psutil
            metrics['system_health'].update({
                'cpu': psutil.cpu_percent(),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent
            })
        except ImportError:
            pass
        
        # 检查告警条件
        if metrics['current']['error_count'] > 100:
            metrics['alerts'].append({
                'level': 'high',
                'message': 'High error rate detected',
                'count': metrics['current']['error_count']
            })
        
        if metrics['system_health']['cpu'] > 80:
            metrics['alerts'].append({
                'level': 'warning',
                'message': 'High CPU usage',
                'value': metrics['system_health']['cpu']
            })
        
        return metrics

    def export_error_report(self, format='pdf'):
        """导出错误报告"""
        from django.template.loader import render_to_string
        from weasyprint import HTML
        import json
        
        # 获取报告数据
        report_data = self.generate_error_report()
        
        if format == 'pdf':
            # 渲染HTML模板
            html_content = render_to_string('reports/error_report.html', {
                'report': report_data,
                'generated_at': timezone.now()
            })
            
            # 生成PDF
            pdf = HTML(string=html_content).write_pdf()
            return ('error_report.pdf', pdf, 'application/pdf')
            
        elif format == 'json':
            # 导出JSON格式
            json_data = json.dumps(report_data, indent=2)
            return ('error_report.json', json_data, 'application/json')
            
        elif format == 'csv':
            # 导出CSV格式
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入头部
            writer.writerow(['Error Type', 'Count', 'Last Seen', 'Impact Level'])
            
            # 写入数据
            for error in report_data['top_errors']:
                writer.writerow([
                    error[0],
                    error[1]['count'],
                    error[1]['last_seen'],
                    'High' if error[1]['count'] > 100 else 'Medium'
                ])
                
            return ('error_report.csv', output.getvalue(), 'text/csv')
        
        else:
            raise ValueError(f"Unsupported format: {format}")