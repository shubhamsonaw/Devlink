from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core.management import get_commands
from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from problems.models import Problem
from solutions.models import Solution

from .models import Application, Connection, Invitation, Message, Opportunity, Project, ProjectTask, ProjectUpdate
from Connect.asgi import application


class ChatWebSocketRoutingTests(SimpleTestCase):
    def test_runserver_uses_daphne_asgi_server(self):
        self.assertEqual(get_commands()['runserver'], 'daphne')

    def test_unauthenticated_chat_socket_is_rejected_by_asgi_route(self):
        async def connect_unauthenticated_socket():
            communicator = WebsocketCommunicator(application, '/ws/chat/admin/')
            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4401)

        async_to_sync(connect_unauthenticated_socket)()


class CollaborationCycleTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='safe-test-password-123')
        self.developer = User.objects.create_user(username='developer', password='safe-test-password-123')
        self.problem = Problem.objects.create(
            user=self.owner,
            title='Improve the search experience',
            description='Make search faster and easier to use.',
            difficulty='medium',
        )
        self.solution = Solution.objects.create(
            user=self.developer,
            problem=self.problem,
            explanation='Use a normalized index and paginate results.',
            is_accepted=True,
        )

    def test_accepting_solution_invitation_connects_and_creates_project(self):
        self.problem.status = 'resolved'
        self.problem.save(update_fields=['status'])
        self.client.force_login(self.owner)
        response = self.client.post(reverse(
            'invite_solution_collaborator', args=[self.solution.id]
        ))
        self.assertEqual(response.status_code, 302)
        invitation = Invitation.objects.get(solution=self.solution)

        self.client.force_login(self.developer)
        response = self.client.post(reverse('accept_invitation', args=[invitation.id]))
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Connection.objects.filter(user1=self.owner, user2=self.developer).exists() |
                        Connection.objects.filter(user1=self.developer, user2=self.owner).exists())
        project = Project.objects.get(source_solution=self.solution)
        self.assertSetEqual(set(project.members.all()), {self.owner, self.developer})
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'open')

    def test_accepting_application_connects_and_creates_project(self):
        opportunity = Opportunity.objects.create(
            user=self.owner,
            title='Build the next search feature',
            description='Collaborate on search improvements.',
            required_skills='Django, Python',
        )
        application = Application.objects.create(
            user=self.developer,
            opportunity=opportunity,
            message='I would like to help.',
        )
        self.client.force_login(self.owner)
        response = self.client.post(reverse('accept_application', args=[application.id]))
        self.assertEqual(response.status_code, 302)

        application.refresh_from_db()
        self.assertEqual(application.status, 'accepted')
        self.assertTrue(Connection.objects.filter(user1=self.owner, user2=self.developer).exists() |
                        Connection.objects.filter(user1=self.developer, user2=self.owner).exists())
        project = Project.objects.get(source_application=application)
        self.assertSetEqual(set(project.members.all()), {self.owner, self.developer})

    def test_only_project_members_can_post_updates_and_updates_are_public(self):
        project = Project.objects.create(
            title='Public collaboration',
            description='A shared project.',
            owner=self.owner,
            source_solution=self.solution,
        )
        project.members.add(self.owner, self.developer)
        self.client.force_login(self.developer)
        response = self.client.post(
            reverse('project_detail', args=[project.id]),
            {'content': 'First progress update.'},
        )
        self.assertEqual(response.status_code, 302)
        update = ProjectUpdate.objects.get(project=project)
        self.assertEqual(update.author, self.developer)

        outsider = User.objects.create_user(username='visitor', password='safe-test-password-123')
        self.client.force_login(outsider)
        response = self.client.get(reverse('project_detail', args=[project.id]))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse('project_detail', args=[project.id]),
            {'content': 'Unauthorized update.'},
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(ProjectUpdate.objects.filter(project=project).count(), 1)

    def test_project_tasks_assignment_status_and_completion_lifecycle(self):
        project = Project.objects.create(title='Search project', owner=self.owner)
        project.members.add(self.owner, self.developer)

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('create_project_task', args=[project.id]),
            {'title': 'Add database index', 'description': 'Measure query time.', 'assigned_to': self.developer.id},
        )
        self.assertEqual(response.status_code, 302)
        task = ProjectTask.objects.get(project=project)
        self.assertEqual(task.assigned_to, self.developer)
        response = self.client.get(reverse('project_detail', args=[project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add a task')
        self.assertContains(response, 'Finish every task before marking this project complete.')

        response = self.client.post(
            reverse('set_project_status', args=[project.id]), {'status': 'completed'}
        )
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, 'active')
        self.assertIsNone(project.completed_at)

        self.client.force_login(self.developer)
        response = self.client.post(
            reverse('update_project_task_status', args=[task.id]), {'status': 'in_progress'}
        )
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, 'in_progress')

        self.client.force_login(self.owner)
        self.client.post(reverse('update_project_task_status', args=[task.id]), {'status': 'done'})
        response = self.client.post(
            reverse('set_project_status', args=[project.id]), {'status': 'completed'}
        )
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, 'completed')
        self.assertIsNotNone(project.completed_at)

        self.client.force_login(self.developer)
        self.client.post(
            reverse('update_project_task_status', args=[task.id]), {'status': 'todo'}
        )
        task.refresh_from_db()
        self.assertEqual(task.status, 'done')

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('set_project_status', args=[project.id]), {'status': 'active'}
        )
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, 'active')
        self.assertIsNone(project.completed_at)

    def test_non_member_cannot_create_project_task(self):
        project = Project.objects.create(title='Private work controls', owner=self.owner)
        outsider = User.objects.create_user(username='outsider', password='safe-test-password-123')
        self.client.force_login(outsider)
        response = self.client.post(
            reverse('create_project_task', args=[project.id]), {'title': 'Unauthorized task'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectTask.objects.filter(project=project).exists())

    def test_reopening_solution_project_reopens_resolved_problem(self):
        self.problem.status = 'resolved'
        self.problem.save(update_fields=['status'])
        project = Project.objects.create(
            title='Search collaboration',
            owner=self.owner,
            source_solution=self.solution,
            status='completed',
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('set_project_status', args=[project.id]), {'status': 'active'}
        )
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.problem.refresh_from_db()
        self.assertEqual(project.status, 'active')
        self.assertEqual(project.completed_at, None)
        self.assertEqual(self.problem.status, 'open')

    def test_non_owner_cannot_invite_solver(self):
        self.client.force_login(self.developer)
        response = self.client.post(reverse(
            'invite_solution_collaborator', args=[self.solution.id]
        ))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Invitation.objects.filter(solution=self.solution).exists())

    def test_opportunity_detail_and_accepted_solution_list_render(self):
        opportunity = Opportunity.objects.create(
            user=self.owner,
            title='Build the next search feature',
            description='Collaborate on search improvements.',
            required_skills='Django, Python',
        )
        response = self.client.get(reverse('opportunity_detail', args=[opportunity.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Log in to apply')

        self.client.force_login(self.owner)
        response = self.client.get(reverse('solution_list', args=[self.problem.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invite to collaborate')

    def test_homepage_keeps_original_sections_and_sidebar_menu(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'css/theme.css')
        self.assertContains(response, 'Build. Solve. Collaborate.')
        self.assertContains(response, 'Trending Problems')
        self.assertContains(response, 'Top Contributors')
        self.assertContains(response, 'Latest Solutions')

    def test_chat_messages_are_not_rendered_as_site_alerts(self):
        Connection.objects.create(user1=self.owner, user2=self.developer)
        Message.objects.create(
            sender=self.owner,
            receiver=self.developer,
            content='A message inside the conversation.',
        )
        self.client.force_login(self.developer)

        response = self.client.get(reverse('chat', args=[self.owner.username]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A message inside the conversation.')
        self.assertNotContains(response, 'owner → developer')
        self.assertContains(response, 'id="sidebar-toggle"')
