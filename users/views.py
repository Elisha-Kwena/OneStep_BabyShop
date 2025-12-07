# views.py
from rest_framework import generics, status, views,permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .models import CustomUser,PasswordResetToken
from .serializers import (
    RegisterSerializer, 
    VerifyEmailSerializer,
    ResendVerificationSerializer,
    VerifiedEmailLoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer
)
# Import the HTML email helper functions
from .utils import send_verification_email, send_welcome_email

# Helper: generate JWT tokens
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Check if email was sent successfully
        email_sent = getattr(serializer, '_email_sent', True)
        
        response_data = {
            "success": True,
            "message": _("Registration successful."),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "phone": user.phone,
                "is_email_verified": user.is_email_verified
            }
        }
        
        if email_sent:
            response_data.update({
                "message": _("Registration successful. Please check your email for verification code."),
                "note": _("A 6-digit verification code has been sent to your email. It expires in 24 hours.")
            })
        else:
            response_data.update({
                "warning": _("Registration successful, but we couldn't send the verification email."),
                "note": _("Please use the resend verification feature to get your code.")
            })

        return Response(response_data, status=status.HTTP_201_CREATED)


class VerifyEmailView(generics.GenericAPIView):
    """Verify email with 6-digit code"""
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send welcome email after verification
        welcome_sent = send_welcome_email(user)
        
        response_data = {
            "success": True,
            "message": _("Email verified successfully! You can now login."),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_email_verified": user.is_email_verified,
                "email_verified_at": user.email_verified_at
            }
        }
        
        if not welcome_sent:
            response_data["note"] = _("Welcome email could not be sent, but your email is verified.")

        return Response(response_data, status=status.HTTP_200_OK)


class ResendVerificationView(generics.GenericAPIView):
    """Resend verification code"""
    serializer_class = ResendVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            
            # Use the HTML email helper directly
            email_sent = send_verification_email(user, is_resend=True)
            
            if email_sent:
                return Response({
                    "success": True,
                    "message": _("New verification code sent to your email."),
                    "note": _("The code expires in 24 hours."),
                    "email": user.email
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": _("Failed to send verification email. Please try again."),
                    "email": user.email
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                "success": False,
                "error": _("An error occurred while processing your request."),
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Optional: Enhanced view to check verification status with more details
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_verification_status(request):
    """Check if current user's email is verified with detailed info"""
    user = request.user
    
    # Calculate if verification code is expired
    verification_info = None
    if user.email_verification_sent_at and not user.is_email_verified:
        from django.utils import timezone
        from datetime import timedelta
        
        expiry_time = user.email_verification_sent_at + timedelta(hours=24)
        is_expired = timezone.now() > expiry_time
        
        verification_info = {
            "code_sent": bool(user.email_verification_code),
            "sent_at": user.email_verification_sent_at,
            "expires_at": expiry_time,
            "is_expired": is_expired,
            "can_resend": is_expired or (timezone.now() - user.email_verification_sent_at).total_seconds() > 120  # 2 minutes
        }
    
    return Response({
        "is_email_verified": user.is_email_verified,
        "email": user.email,
        "email_verified_at": user.email_verified_at,
        "verification_info": verification_info
    })


# Optional: View to manually trigger email sending (for testing)
@api_view(['POST'])
@permission_classes([AllowAny])
def send_test_email(request):
    """Test endpoint to send verification email (for development only)"""
    if not settings.DEBUG:
        return Response({
            "error": _("This endpoint is only available in debug mode.")
        }, status=status.HTTP_403_FORBIDDEN)
    
    email = request.data.get('email')
    if not email:
        return Response({
            "error": _("Email is required.")
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = CustomUser.objects.get(email=email)
        
        # Send verification email
        success = send_verification_email(user, is_resend=False)
        
        if success:
            return Response({
                "success": True,
                "message": _("Test verification email sent."),
                "email": user.email,
                "verification_code": user.email_verification_code  # For testing
            })
        else:
            return Response({
                "success": False,
                "error": _("Failed to send email."),
                "email": user.email
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except CustomUser.DoesNotExist:
        return Response({
            "error": _("User not found.")
        }, status=status.HTTP_404_NOT_FOUND)


# Optional: View to send welcome email manually
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_welcome_email_view(request):
    """Manually send welcome email (for testing or if initial send failed)"""
    user = request.user
    
    if not user.is_email_verified:
        return Response({
            "error": _("Please verify your email first.")
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success = send_welcome_email(user)
    
    if success:
        return Response({
            "success": True,
            "message": _("Welcome email sent successfully."),
            "email": user.email
        })
    else:
        return Response({
            "success": False,
            "error": _("Failed to send welcome email."),
            "email": user.email
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


class VerifiedEmailLoginView(TokenObtainPairView):
    """Simple view that uses our verified email serializer"""
    serializer_class = VerifiedEmailLoginSerializer


class LogoutView(generics.GenericAPIView):
    serializer_class =LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()

            return Response({
                "success": True,
                "message": _("Successfully logged out."),
                "detail": _("Your session has been terminated. Please delete tokens from client storage.")
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
class LogoutAllView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self,request):
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            tokens = OutstandingToken.objects.filter(user=request.user)
            
            for token in tokens:
                try:
                    RefreshToken(token.token).blacklist()
                except TokenError:
                    pass
            return Response({
                "success":True,
                "message":_("Successfuly logged out from all devices"),
                "devices_logged_out":tokens.count()
            },status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "success":False,
                "error":str(e)
            },status=status.HTTP_400_BAD_REQUEST)
        



class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self,request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)


        user= serializer.validated_data.get('user')

        # creatingreset token
        reset_token = PasswordResetToken.objects.create(user=user)

        # send request email
        from .utils import send_password_reset_email
        email_sent = send_password_reset_email(user,reset_token.token)


        if email_sent:
            return Response({
                "success":True,
                "message":"Password reset link has been sent to your email",
                "note":"The link expires in 1 hour"
            },status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self,request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        from .utils import send_password_reset_success_email
        send_password_reset_success_email(user, request)
        
        return Response({
            "success":True,
            "message":"Password has been reset successfully",
            "user":{
                "id":user.id,
                "email":user.email
            }
        })   
    

class PasswordResetTokenValidateView(generics.GenericAPIView):
    permission_classes=[permissions.AllowAny]

    def get(self, request,token):
        try:
            reset_token = PasswordResetToken.objects.get(token=token)

            if reset_token.is_valid():
                return Response({
                    "valid":True,
                    "email":reset_token.user.email,
                    "expires_at":reset_token.expires_at
                },status=status.HTTP_200_OK)
            else:
                return Response({
                    "valid":False,
                    "error":"Token has expired or already been used."
                },status=status.HTTP_400_BAD_REQUEST)
        except PasswordResetToken.DoesNotExist:
            return Response({
                "valid":False,
                "error":"Invalid reset Token"
            },status=status.HTTP_404_NOT_FOUND)