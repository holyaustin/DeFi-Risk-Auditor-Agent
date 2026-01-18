import os
import snowflake.connector
from datetime import datetime
from typing import Dict, Any, List


class SnowflakeDB:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Connect to Snowflake database."""
        try:
            self.conn = snowflake.connector.connect(
                user=os.getenv('SNOWFLAKE_USER'),
                password=os.getenv('SNOWFLAKE_PASSWORD'),
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                database=os.getenv('SNOWFLAKE_DATABASE', 'AGENTBEATS'),
                schema=os.getenv('SNOWFLAKE_SCHEMA', 'LEADERBOARDS')
            )
        except Exception as e:
            print(f"Snowflake connection error: {e}")
            self.conn = None
    
    async def store_results(self, agent_id: str, scores: Dict[str, float], findings_count: int):
        """Store evaluation results in Snowflake."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS defi_risk_leaderboard (
                    id INTEGER AUTOINCREMENT,
                    agent_id VARCHAR(255),
                    overall_score FLOAT,
                    detection_score FLOAT,
                    severity_score FLOAT,
                    fix_score FLOAT,
                    reproducibility_score FLOAT,
                    findings_count INTEGER,
                    false_positives INTEGER,
                    submission_time TIMESTAMP,
                    PRIMARY KEY (id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO defi_risk_leaderboard 
                (agent_id, overall_score, detection_score, severity_score, fix_score, 
                 reproducibility_score, findings_count, false_positives, submission_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                agent_id,
                scores.get('overall', 0),
                scores.get('detection', 0),
                scores.get('severity_accuracy', 0),
                scores.get('fix_quality', 0),
                scores.get('reproducibility', 0),
                findings_count,
                scores.get('false_positives', 0),
                datetime.utcnow()
            ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Snowflake insert error: {e}")
            return False
    
    async def get_leaderboard(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve leaderboard data from Snowflake."""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    agent_id,
                    overall_score,
                    detection_score,
                    severity_score,
                    fix_score,
                    reproducibility_score,
                    findings_count,
                    false_positives,
                    submission_time
                FROM defi_risk_leaderboard
                ORDER BY overall_score DESC
                LIMIT %s
            """, (limit,))
            
            results = []
            for row in cursor:
                results.append({
                    'agent_id': row[0],
                    'overall_score': row[1],
                    'detection_score': row[2],
                    'severity_score': row[3],
                    'fix_score': row[4],
                    'reproducibility_score': row[5],
                    'findings_count': row[6],
                    'false_positives': row[7],
                    'submission_time': row[8].isoformat() if row[8] else None
                })
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"Snowflake query error: {e}")
            return []