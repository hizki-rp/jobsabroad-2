from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.db import transaction
from .models import University, UserDashboard, UniversityJSONImport, ScholarshipResult, CountryJobSite, CountryJobSiteJSONImport
from .serializers import UniversitySerializer
from .scholarship_service import ScholarshipOwlService
import json

# Register your models here.
admin.site.register(UserDashboard)

@admin.register(UniversityJSONImport)
class UniversityJSONImportAdmin(admin.ModelAdmin):
    """
    Custom admin view to allow creating universities by pasting JSON data.
    """
    list_display = ('created_at',)
    ordering = ('-created_at',)
    # Define fields for the "add" page
    fields = ('json_data',)

    def save_model(self, request, obj, form, change):
        json_data_str = form.cleaned_data.get('json_data')
        if not json_data_str:
            self.message_user(request, "JSON data field cannot be empty.", level=messages.WARNING)
            return

        # Process universities first, then save the import object
        created_count = 0
        skipped_count = 0
        error_occurred = False
        
        try:
            data = json.loads(json_data_str)
            
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                try:
                    # Remove id field completely
                    item.pop('id', None)
                    
                    # Skip if university with same name AND country already exists
                    if University.objects.filter(
                        name=item.get('name', ''),
                        country=item.get('country', '')
                    ).exists():
                        skipped_count += 1
                        continue
                    
                    # Create university directly using ORM
                    university = University.objects.create(
                        name=item.get('name', ''),
                        country=item.get('country', ''),
                        city=item.get('city', ''),
                        course_offered=item.get('course_offered', ''),
                        application_fee=item.get('application_fee', '0.00'),
                        tuition_fee=item.get('tuition_fee', '0.00'),
                        intakes=item.get('intakes', []),
                        bachelor_programs=item.get('bachelor_programs', []),
                        masters_programs=item.get('masters_programs', []),
                        scholarships=item.get('scholarships', []),
                        university_link=item.get('university_link', ''),
                        application_link=item.get('application_link', ''),
                        description=item.get('description', '')
                    )
                    created_count += 1
                except Exception as item_error:
                    print(f"Error creating university {item.get('name', 'Unknown')}: {item_error}")
                    error_occurred = True
                    continue
            
            # Only save the import object after universities are created
            super().save_model(request, obj, form, change)
            
            if created_count > 0:
                self.message_user(request, f"Successfully imported {created_count} university/universities. {skipped_count} skipped (already exist).", level=messages.SUCCESS)
            elif error_occurred:
                self.message_user(request, f"Import completed with errors. {skipped_count} universities already existed.", level=messages.WARNING)
            else:
                self.message_user(request, f"No new universities created. {skipped_count} already exist.", level=messages.WARNING)
                
        except json.JSONDecodeError:
            self.message_user(request, "Invalid JSON format.", level=messages.ERROR)
        except Exception as e:
            self.message_user(request, f"An error occurred during import: {e}", level=messages.ERROR)

    def has_change_permission(self, request, obj=None):
        # This view is for adding (importing) only. No editing of past imports.
        return False

@admin.register(ScholarshipResult)
class ScholarshipResultAdmin(admin.ModelAdmin):
    list_display = ('country', 'total_count', 'fetched_at')
    list_filter = ('country', 'fetched_at')
    readonly_fields = ('scholarships_data', 'fetched_at', 'total_count', 'formatted_scholarships')
    fields = ('country', 'formatted_scholarships', 'total_count', 'fetched_at')
    
    def formatted_scholarships(self, obj):
        if not obj.scholarships_data:
            return "No scholarships"
        
        html = "<div style='max-height: 400px; overflow-y: auto;'>"
        for i, scholarship in enumerate(obj.scholarships_data[:10], 1):
            html += f"<div style='border: 1px solid #ddd; margin: 5px; padding: 10px;'>"
            html += f"<strong>{i}. {scholarship.get('name', 'N/A')}</strong><br>"
            html += f"Coverage: {scholarship.get('coverage', 'N/A')}<br>"
            html += f"Eligibility: {scholarship.get('eligibility', 'N/A')}<br>"
            if scholarship.get('link'):
                html += f"<a href='{scholarship['link']}' target='_blank'>View Details</a>"
            html += "</div>"
        if len(obj.scholarships_data) > 10:
            html += f"<p><em>... and {len(obj.scholarships_data) - 10} more scholarships</em></p>"
        html += "</div>"
        return format_html(html)
    
    formatted_scholarships.short_description = "Scholarships Preview"
    
    def save_model(self, request, obj, form, change):
        if not change:
            service = ScholarshipOwlService()
            scholarships = service.get_scholarships(country=obj.country, limit=50)
            obj.scholarships_data = scholarships
            obj.total_count = len(scholarships)
        super().save_model(request, obj, form, change)

class UniversityDataAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'program_count', 'scholarship_count', 'has_image')
    list_filter = ('country',)
    readonly_fields = ('formatted_programs', 'formatted_scholarships_detail', 'image_preview')
    fields = ('name', 'country', 'image_url', 'image_preview', 'formatted_scholarships_detail', 'formatted_programs')
    
    def has_image(self, obj):
        return "Yes" if obj.image_url else "No"
    has_image.short_description = "Has Image"
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px; object-fit: cover; border-radius: 8px;" />', obj.image_url)
        return "No image"
    image_preview.short_description = "Image Preview"
    
    def program_count(self, obj):
        return f"{len(obj.bachelor_programs)} bachelor, {len(obj.masters_programs)} masters"
    
    def scholarship_count(self, obj):
        return len(obj.scholarships)
    
    def formatted_scholarships_detail(self, obj):
        if not obj.scholarships:
            return "No scholarships"
        
        html = "<div style='max-height: 300px; overflow-y: auto;'>"
        for i, scholarship in enumerate(obj.scholarships, 1):
            html += f"<div style='border: 1px solid #ddd; margin: 5px; padding: 10px;'>"
            html += f"<strong>{i}. {scholarship.get('name', 'N/A')}</strong><br>"
            html += f"Coverage: {scholarship.get('coverage', 'N/A')}<br>"
            html += f"Eligibility: {scholarship.get('eligibility', 'N/A')}<br>"
            if scholarship.get('link'):
                html += f"<a href='{scholarship['link']}' target='_blank'>View Details</a>"
            html += "</div>"
        html += "</div>"
        return format_html(html)
    
    def formatted_programs(self, obj):
        html = "<div style='max-height: 400px; overflow-y: auto;'>"
        
        if obj.bachelor_programs:
            html += "<h3>Bachelor Programs</h3>"
            for i, program in enumerate(obj.bachelor_programs, 1):
                html += f"<div style='border: 1px solid #e0e0e0; margin: 3px; padding: 8px;'>"
                html += f"<strong>{i}. {program.get('program_name', 'N/A')}</strong><br>"
                html += f"Duration: {program.get('duration_years', 'N/A')} years<br>"
                html += f"Language: {program.get('language', 'N/A')}<br>"
                if program.get('notes'):
                    html += f"Notes: {program.get('notes')}<br>"
                html += "</div>"
        
        if obj.masters_programs:
            html += "<h3>Masters Programs</h3>"
            for i, program in enumerate(obj.masters_programs, 1):
                html += f"<div style='border: 1px solid #e0e0e0; margin: 3px; padding: 8px;'>"
                html += f"<strong>{i}. {program.get('program_name', 'N/A')}</strong><br>"
                html += f"Duration: {program.get('duration_years', 'N/A')} years<br>"
                html += f"Language: {program.get('language', 'N/A')}<br>"
                if program.get('thesis_required'):
                    html += f"Thesis Required: Yes<br>"
                if program.get('notes'):
                    html += f"Notes: {program.get('notes')}<br>"
                html += "</div>"
        
        html += "</div>"
        return format_html(html)
    
    formatted_scholarships_detail.short_description = "Scholarships"
    formatted_programs.short_description = "Programs"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(University, UniversityDataAdmin)

@admin.register(CountryJobSite)
class CountryJobSiteAdmin(admin.ModelAdmin):
    list_display = ("country", "site_name", "site_url")
    list_filter = ("country",)
    search_fields = ("country", "site_name", "site_url")
    ordering = ("country", "site_name")

@admin.register(CountryJobSiteJSONImport)
class CountryJobSiteJSONImportAdmin(admin.ModelAdmin):
    """
    Custom admin view to allow creating country job sites by pasting JSON data.
    """
    list_display = ("id", "created_at")
    readonly_fields = ("created_at",)
    
    def save_model(self, request, obj, form, change):
        import json
        from django.contrib import messages
        
        # First save the import record
        super().save_model(request, obj, form, change)
        
        # Then process the JSON
        try:
            data = json.loads(obj.json_data)
            
            # Ensure data is a list
            if not isinstance(data, list):
                messages.error(request, "JSON must be an array of objects")
                return
            
            created_count = 0
            updated_count = 0
            errors = []
            
            for idx, item in enumerate(data):
                try:
                    country = item.get('country')
                    site_name = item.get('site_name')
                    site_url = item.get('site_url')
                    
                    if not all([country, site_name, site_url]):
                        errors.append(f"Row {idx + 1}: Missing required fields")
                        continue
                    
                    # Create or update job site
                    job_site, created = CountryJobSite.objects.update_or_create(
                        country=country,
                        site_name=site_name,
                        defaults={'site_url': site_url}
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    errors.append(f"Row {idx + 1}: {str(e)}")
            
            # Show results
            if created_count > 0:
                messages.success(request, f"Successfully created {created_count} job site(s)")
            if updated_count > 0:
                messages.info(request, f"Updated {updated_count} existing job site(s)")
            if errors:
                for error in errors[:5]:
                    messages.warning(request, error)
                if len(errors) > 5:
                    messages.warning(request, f"... and {len(errors) - 5} more errors")
                    
        except json.JSONDecodeError as e:
            messages.error(request, f"Invalid JSON: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error processing JSON: {str(e)}")