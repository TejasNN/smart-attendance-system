import logging
from typing import Optional, Dict, List, Any
from backend.fastapi_app.db.repos.device_repo import DeviceRepository
from backend.fastapi_app.services.device_service import DeviceService
from backend.fastapi_app.db.repos.assignment_repo import AssignmentRepository
from desktop_app.utils.utils import current_datetime_utc

logger = logging.getLogger(__name__)


class AdminService:
    """
    Core provisioning engine. No API exposure here — this is pure service layer.
    """
    def __init__(self, postgres, mongo):
        self.device_repo = DeviceRepository(postgres)
        self.device_service = DeviceService(postgres, mongo)
        self.assignment_repo = AssignmentRepository(postgres)
        self.mongo_db = mongo


    def list_pending_devices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Return devices with status = 'pending'
        """
        try:
            rows = self.device_repo.get_pending_devices(limit=limit)
            return rows
        except Exception as e:
                logger.exception(f"Failed to list pending devices: {e}")
                raise
    
    def list_all_devices(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            rows = self.device_repo.get_all_devices(limit=limit)
            return rows
        except Exception as e:
                logger.exception(f"Failed to list all devices: {e}")
                raise

    
    def get_device_details(self, device_id: int) -> Dict[str, Any]:
        """
        Returns detailed device info including assignments and recent device logs.
        """
        dev = self.device_repo.get_by_id(device_id)
        if not dev:
            return None
        
        assignments = self.assignment_repo.get_assignments_for_device(device_id)

        try:
            logs = self.mongo_db.get_device_logs(device_id, limit=50)
        except Exception as e:
            logger.warning(f"Failed to fetch logs for device {device_id}: {e}")
            logs = []

        return {
            "device": dev,
            "assignments": assignments,
            "recent_logs": logs
        }

    
    def approve_device(self, device_id: int, approver_employee_id: int) -> bool:
        """
        Approve the device using DeviceService (keeps audit logging in MongoDB).
        Returns True on success.
        """
        approve = self.device_service.approve_device(device_id, approver_employee_id)
        return approve
    

    def reject_device(self, device_id: int, approver_employee_id: int) -> str:
        """
        Reject a device if status == 'pending'and Revoke a device
        if status == 'active' and log the events in mongo
        Returns status.
        """
        try:
            dev = self.device_repo.get_by_id(device_id)
            if not dev:
                raise ValueError(f"Device {device_id} not found")
            
            device_uuid = dev.get("device_uuid") if dev else None

            if dev['status'] == 'pending':
                # provisioning rejection
                status = "rejected"
                self.device_repo.update_status(device_id, status=status)

                self.mongo_db.log_device_event(
                    device_id=device_id,
                    device_uuid=device_uuid,
                    user_id=approver_employee_id,
                    event_type="reject_pending_device",
                    details={
                        "reason": "rejected before approval"
                    }
                )
                return status
            elif dev["status"] == "active":
                # device removal after approval
                status = "revoked"
                self.assignment_repo.remove_assignments(device_id)
                self.device_repo.clear_token(device_id)
                self.device_repo.update_status(device_id, status=status)
                
                self.mongo_db.log_device_event(
                    device_id=device_id,
                    device_uuid=device_uuid,
                    user_id=approver_employee_id,
                    event_type="reject_approved_device",
                    details={
                        "reason": "device revoked by admin"
                    }
                )
                return status
        except Exception as e:
            logger.exception(f"Failed to reject device {device_id}: {e}")
            raise

    
    def force_reset_token(self, device_id: int, admin_id: int) -> bool:
        """
        Clear credential_hash so device must fetch a new token later.
        """
        try:
            self.device_repo.clear_token(device_id)
            dev = self.device_repo.get_by_id(device_id)
            if not dev:
                raise ValueError("Device not found after clearing token")
            
            device_uuid = dev.get("device_uuid") if dev else None
            
            self.mongo_db.log_device_event(
                device_id=device_id,
                device_uuid=device_uuid,
                user_id=admin_id,
                event_type="force_reset_token",
                details={
                    "timestamp": current_datetime_utc()
                }
            )
            return True
        except Exception as e:
                logger.exception(f"Failed to force reset token for device {device_id}: {e}")
                raise


    def assign_users(self, device_id: int, employee_ids: List[int], assigned_by: int) -> Dict[str, Any]:
        """
        Assign multiple employee_ids to a device.
        Returns a summary dict { assigned_count, requested_count }
        """
        # Validate device exists
        dev = self.device_repo.get_by_id(device_id)
        if not dev:
            raise ValueError("device not found")
        
        # Validate employee ids exist (users table uses employee_id)
        valid_employees = self.assignment_repo.validate_employees(employee_ids)
        if not valid_employees:
            raise ValueError("No valid employees found")
        
        invalid = [emp for emp in employee_ids if emp not in valid_employees]
        to_insert = valid_employees

        try:
            if to_insert:
                result = self.assignment_repo.assign_users_to_device(device_id, to_insert, assigned_by)
                created_count = result
            else:
                created_count = 0

            assignments = self.assignment_repo.get_assignments_for_device(device_id)
            
            return {
                "assigned": True,
                "requested": len(employee_ids),
                "created_count": created_count,
                "invalid_employee_ids": invalid,
                "assignments": assignments
            }
        except Exception as e:
            logger.exception(f"Failed assigning users to device {device_id}: {e}")
            raise
