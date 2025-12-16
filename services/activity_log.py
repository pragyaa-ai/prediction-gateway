"""
Activity logging service for admin actions
"""
from datetime import datetime
from typing import List, Dict, Any
import json
from pathlib import Path


class ActivityLogger:
    """Log and track all admin activities"""
    
    def __init__(self, log_file: str = "logs/activity.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log_activity(
        self,
        user_email: str,
        user_name: str,
        action: str,
        details: Dict[str, Any],
        status: str = "success"
    ):
        """Log an admin activity"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_email": user_email,
            "user_name": user_name,
            "action": action,
            "details": details,
            "status": status
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"Failed to log activity: {e}")
    
    def get_recent_activities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activities"""
        if not self.log_file.exists():
            return []
        
        activities = []
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                # Get last N lines
                for line in lines[-limit:]:
                    activities.append(json.loads(line.strip()))
            
            # Return in reverse order (newest first)
            return list(reversed(activities))
        except Exception as e:
            print(f"Failed to read activities: {e}")
            return []
    
    def get_activities_by_user(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activities for a specific user"""
        all_activities = self.get_recent_activities(limit=1000)
        user_activities = [
            a for a in all_activities 
            if a.get("user_email") == user_email
        ]
        return user_activities[:limit]
    
    def get_activities_by_action(self, action: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activities for a specific action type"""
        all_activities = self.get_recent_activities(limit=1000)
        action_activities = [
            a for a in all_activities 
            if a.get("action") == action
        ]
        return action_activities[:limit]


# Global activity logger
activity_logger = ActivityLogger()
