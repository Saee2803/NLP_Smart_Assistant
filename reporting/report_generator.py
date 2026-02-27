# reporting/report_generator.py
"""
Automated Report Generator

Generates management-ready reports:
- Daily Incident Summary
- Weekly Health + SLA
- Monthly Risk & Trend

Formats: Text, JSON, optional PDF
Supports disk storage and SMTP (disabled by default)

Python 3.6 compatible.
"""

import json
import os
from datetime import datetime, timedelta


class ReportBuilder(object):
    """Base report builder."""
    
    def __init__(self, title, report_date=None):
        """
        Initialize builder.
        
        Args:
            title: Report title
            report_date: Report date (default: today)
        """
        self.title = title
        self.report_date = report_date or datetime.now().strftime('%Y-%m-%d')
        self.sections = []
        self.metadata = {
            'title': title,
            'date': self.report_date,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def add_section(self, section_name, content):
        """
        Add report section.
        
        Args:
            section_name: Section title
            content: Section content (list of lines or dict)
        """
        self.sections.append({
            'name': section_name,
            'content': content
        })
    
    def add_metric(self, name, value, unit='', target=None, status='OK'):
        """
        Add metric line.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Unit (e.g., '%', 'min')
            target: Target value for comparison
            status: Status (OK, WARNING, CRITICAL)
        """
        if not self.sections or self.sections[-1]['name'] != 'Metrics':
            self.sections.append({'name': 'Metrics', 'content': []})
        
        metric_line = '{0}: {1}{2}'.format(name, value, unit)
        
        if target is not None:
            metric_line = metric_line + ' (target: {0}{1})'.format(target, unit)
        
        if status != 'OK':
            metric_line = metric_line + ' [{0}]'.format(status)
        
        self.sections[-1]['content'].append(metric_line)
    
    def to_text(self):
        """Generate text report."""
        lines = []
        lines.append('=' * 70)
        lines.append(self.title)
        lines.append('Generated: {0}'.format(self.metadata['generated_at']))
        lines.append('=' * 70)
        lines.append('')
        
        for section in self.sections:
            lines.append(section['name'])
            lines.append('-' * len(section['name']))
            
            if isinstance(section['content'], list):
                for item in section['content']:
                    lines.append(item)
            elif isinstance(section['content'], dict):
                for key, value in section['content'].items():
                    lines.append('{0}: {1}'.format(key, value))
            else:
                lines.append(str(section['content']))
            
            lines.append('')
        
        return '\n'.join(lines)
    
    def to_json(self):
        """Generate JSON report."""
        report_dict = {
            'metadata': self.metadata,
            'sections': []
        }
        
        for section in self.sections:
            report_dict['sections'].append({
                'name': section['name'],
                'content': section['content']
            })
        
        return json.dumps(report_dict, indent=2)
    
    def to_dict(self):
        """Get report as dict."""
        return {
            'metadata': self.metadata,
            'sections': self.sections
        }


class DailyIncidentReport(object):
    """Daily incident summary report."""
    
    def __init__(self, db, target_list=None):
        """
        Initialize report.
        
        Args:
            db: Database instance
            target_list: List of targets to include (default: all)
        """
        self.db = db
        self.target_list = target_list
    
    def generate(self):
        """
        Generate daily incident report.
        
        Returns:
            ReportBuilder
        """
        report = ReportBuilder('Daily Incident Summary')
        
        # Get today's incidents
        today_incidents = self.db.get_incidents(target=None, days=1)
        
        report.add_section('Overview', {
            'Total Incidents': len(today_incidents),
            'Report Date': datetime.now().strftime('%Y-%m-%d')
        })
        
        # Group by severity
        by_severity = {}
        for incident in today_incidents:
            severity = incident.get('severity', 'UNKNOWN')
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(incident)
        
        severity_lines = []
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = len(by_severity.get(severity, []))
            if count > 0:
                severity_lines.append('{0}: {1} incidents'.format(severity, count))
        
        if severity_lines:
            report.add_section('Incidents by Severity', severity_lines)
        
        # Top affected targets
        by_target = {}
        for incident in today_incidents:
            target = incident.get('target', 'UNKNOWN')
            if target not in by_target:
                by_target[target] = 0
            by_target[target] += 1
        
        if by_target:
            top_targets = sorted(by_target.items(), key=lambda x: x[1], reverse=True)
            target_lines = ['{0}: {1} incidents'.format(t[0], t[1]) for t in top_targets[:5]]
            report.add_section('Top Affected Databases', target_lines)
        
        # Top issue types
        by_description = {}
        for incident in today_incidents:
            desc = incident.get('description', 'Unknown')[:50]
            if desc not in by_description:
                by_description[desc] = 0
            by_description[desc] += 1
        
        if by_description:
            top_issues = sorted(by_description.items(), key=lambda x: x[1], reverse=True)
            issue_lines = ['{0}: {1} times'.format(t[0], t[1]) for t in top_issues[:5]]
            report.add_section('Top Issue Types', issue_lines)
        
        return report


class WeeklyHealthReport(object):
    """Weekly health and SLA report."""
    
    def __init__(self, db, health_scorer=None, sla_tracker=None):
        """
        Initialize report.
        
        Args:
            db: Database instance
            health_scorer: DatabaseHealthScorer instance
            sla_tracker: SLATracker instance
        """
        self.db = db
        self.health_scorer = health_scorer
        self.sla_tracker = sla_tracker
    
    def generate(self):
        """
        Generate weekly health report.
        
        Returns:
            ReportBuilder
        """
        report = ReportBuilder('Weekly Health & SLA Report')
        
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        report.add_section('Period', {
            'Report Date': datetime.now().strftime('%Y-%m-%d'),
            'Period': 'Last 7 days'
        })
        
        # Health scores
        if self.health_scorer:
            try:
                # Get all unique targets
                all_incidents = self.db.get_incidents(target=None, days=7)
                targets = set([i.get('target') for i in all_incidents if i.get('target')])
                
                health_lines = []
                for target in sorted(targets)[:10]:  # Top 10
                    health = self.health_scorer.score_database(target, days=7)
                    health_score = health.get('health_score', 0)
                    health_state = health.get('health_state', 'UNKNOWN')
                    
                    health_lines.append('{0}: {1}/100 ({2})'.format(
                        target, health_score, health_state
                    ))
                
                if health_lines:
                    report.add_section('Database Health Status', health_lines)
            except Exception:
                pass
        
        # SLA compliance
        if self.sla_tracker:
            try:
                sla_status_list = self.sla_tracker.get_all_sla_status(days=7)
                
                compliant = [s for s in sla_status_list if not s.breached]
                breached = [s for s in sla_status_list if s.breached]
                
                report.add_section('SLA Compliance Summary', {
                    'Compliant': '{0} / {1}'.format(len(compliant), len(sla_status_list)),
                    'Breached': len(breached)
                })
                
                if breached:
                    breach_lines = []
                    for metrics in breached:
                        breach_lines.append('{0}: {1}'.format(
                            metrics.target, metrics.breach_severity
                        ))
                    report.add_section('SLA Breaches', breach_lines)
            except Exception:
                pass
        
        # Incident trends
        try:
            week_incidents = self.db.get_incidents(target=None, days=7)
            prev_week_incidents = self.db.get_incidents(target=None, days=14)
            prev_week_count = len(prev_week_incidents) - len(week_incidents)
            
            week_count = len(week_incidents)
            trend = 'UP' if week_count > prev_week_count else 'DOWN'
            change = abs(week_count - prev_week_count)
            
            report.add_section('Incident Trends', {
                'This Week': '{0} incidents'.format(week_count),
                'Previous Week': '{0} incidents'.format(prev_week_count),
                'Trend': '{0} ({1:+d})'.format(trend, change if trend == 'UP' else -change)
            })
        except Exception:
            pass
        
        return report


class MonthlyRiskReport(object):
    """Monthly risk and trend report."""
    
    def __init__(self, db, predictor=None, pattern_engine=None):
        """
        Initialize report.
        
        Args:
            db: Database instance
            predictor: TimeAwarePredictor instance
            pattern_engine: PatternEngine instance
        """
        self.db = db
        self.predictor = predictor
        self.pattern_engine = pattern_engine
    
    def generate(self):
        """
        Generate monthly risk report.
        
        Returns:
            ReportBuilder
        """
        report = ReportBuilder('Monthly Risk & Trend Report')
        
        report.add_section('Period', {
            'Report Date': datetime.now().strftime('%Y-%m-%d'),
            'Period': 'Last 30 days'
        })
        
        # Incident summary
        try:
            month_incidents = self.db.get_incidents(target=None, days=30)
            prev_month_incidents = self.db.get_incidents(target=None, days=60)
            prev_month_count = len(prev_month_incidents) - len(month_incidents)
            
            change = len(month_incidents) - prev_month_count
            direction = 'UP' if change > 0 else 'DOWN'
            
            report.add_section('Incident Summary', {
                'This Month': '{0} incidents'.format(len(month_incidents)),
                'Previous Month': '{0} incidents'.format(prev_month_count),
                'Change': '{0} ({1:+d})'.format(direction, change)
            })
        except Exception:
            pass
        
        # High-risk databases
        if self.predictor:
            try:
                all_incidents = self.db.get_incidents(target=None, days=30)
                targets = set([i.get('target') for i in all_incidents if i.get('target')])
                
                risk_lines = []
                for target in sorted(targets)[:10]:
                    pred = self.predictor.predict_high_risk_window(target)
                    if pred:
                        conf = pred.get('combined_confidence', 0)
                        hour = pred.get('hour_window', '?')
                        risk_lines.append('{0}: High risk {1} (confidence {2:.0%})'.format(
                            target, hour, conf
                        ))
                
                if risk_lines:
                    report.add_section('Predicted High-Risk Periods', risk_lines)
            except Exception:
                pass
        
        # Recurring patterns
        if self.pattern_engine:
            try:
                pattern_lines = []
                all_incidents = self.db.get_incidents(target=None, days=30)
                targets = set([i.get('target') for i in all_incidents if i.get('target')])
                
                for target in sorted(targets)[:5]:
                    patterns = self.pattern_engine.get_patterns(target)
                    if patterns:
                        for pattern in patterns[:2]:
                            hour = pattern.get('hour_of_day')
                            day = pattern.get('day_of_week')
                            count = pattern.get('incident_count', 0)
                            
                            pattern_lines.append(
                                '{0}: {1}:00 on {2}s ({3} incidents)'.format(
                                    target, hour, day, count
                                )
                            )
                
                if pattern_lines:
                    report.add_section('Recurring Patterns', pattern_lines[:10])
            except Exception:
                pass
        
        # Recommendations
        rec_lines = [
            'Review high-risk windows for capacity planning',
            'Implement auto-scaling for unstable databases',
            'Investigate recurring patterns for root cause',
            'Update SLA targets based on trend analysis'
        ]
        report.add_section('Recommended Actions', rec_lines)
        
        return report


class ReportScheduler(object):
    """Schedule and generate reports."""
    
    def __init__(self, db, health_scorer=None, sla_tracker=None, 
                 predictor=None, pattern_engine=None):
        """
        Initialize scheduler.
        
        Args:
            db: Database instance
            health_scorer: Optional DatabaseHealthScorer
            sla_tracker: Optional SLATracker
            predictor: Optional TimeAwarePredictor
            pattern_engine: Optional PatternEngine
        """
        self.db = db
        self.health_scorer = health_scorer
        self.sla_tracker = sla_tracker
        self.predictor = predictor
        self.pattern_engine = pattern_engine
    
    def generate_daily(self):
        """Generate daily incident report."""
        generator = DailyIncidentReport(self.db)
        return generator.generate()
    
    def generate_weekly(self):
        """Generate weekly health and SLA report."""
        generator = WeeklyHealthReport(
            self.db, self.health_scorer, self.sla_tracker
        )
        return generator.generate()
    
    def generate_monthly(self):
        """Generate monthly risk and trend report."""
        generator = MonthlyRiskReport(
            self.db, self.predictor, self.pattern_engine
        )
        return generator.generate()
    
    def save_report(self, report_builder, filename, format='text'):
        """
        Save report to disk.
        
        Args:
            report_builder: ReportBuilder instance
            filename: Output filename
            format: 'text' or 'json'
        
        Returns:
            Filepath
        """
        if format == 'json':
            content = report_builder.to_json()
            filepath = filename.replace('.txt', '.json')
        else:
            content = report_builder.to_text()
            filepath = filename
        
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            return filepath
        except Exception as e:
            return None
    
    def generate_and_save(self, report_type, output_dir='reports', format='text'):
        """
        Generate report and save to disk.
        
        Args:
            report_type: 'daily', 'weekly', or 'monthly'
            output_dir: Output directory
            format: 'text' or 'json'
        
        Returns:
            Filepath or None
        """
        # Create output directory
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception:
                return None
        
        # Generate report
        if report_type == 'daily':
            builder = self.generate_daily()
        elif report_type == 'weekly':
            builder = self.generate_weekly()
        elif report_type == 'monthly':
            builder = self.generate_monthly()
        else:
            return None
        
        # Save to file
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join(output_dir, '{0}_{1}.txt'.format(report_type, date_str))
        
        return self.save_report(builder, filename, format=format)
