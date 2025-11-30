from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from .views import CourseList, DeployDetailView,TrainingBlockDeployList,backDeploy, CourseDetailView

from . import views

app_name = 'trainingApp'

urlpatterns = [
    path("", login_required(CourseList.as_view()), name="course_list"), 
    path('course/<int:course_id>/', login_required(CourseDetailView.as_view()), name="course_detail"),
    path('blockList/<int:course_id>/<int:training_id>/',  login_required(TrainingBlockDeployList.as_view()), name="block_deploy_list"),
    path("form/<int:course_id>/<int:training_id>/<int:block_id>/", login_required(DeployDetailView.as_view()), name="forms"),
    path("form/<int:course_id>/<int:training_id>/<int:block_id>/backDeploy/", login_required(backDeploy), name="back_deploy"),
    path('reviewList/<int:course_id>/<int:training_id>/', login_required(views.ReviewListTT.as_view()), name="review_list_tt"),
    path('reviewBlock/<int:trainee_training_id>/', login_required(views.ReviewBlock.as_view()), name="review_block"),
    path('review/<int:block_answer_id>/', login_required(views.ReviewDeploy.as_view()), name="review_deploy"),
    path('comment/<int:course_id>/<int:training_id>/', login_required(views.CommentView.as_view()), name="comment")
    
]