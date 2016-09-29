from django.core.management.base import BaseCommand

from kpi.models import Asset, AssetVersion

class Command(BaseCommand):
    ''' This fixup command relies on at least the following assumptions:
    * All deployed assets have `_deployment_data` that contains 'backend'
    * All deployed assets have `_deployment_data` that contains 'version'
    * `_deployment_data['version']` specifies one of the following:
        * `0`, for deployments whose version is unknown due to an earlier bug
        * a string beginning with 'v' that indicates the `uid` of an
            `AssetVersion`
        * something else that indicates the primary key of an `AssetVersion`
    '''
    def handle(self, *args, **options):
        ''' The task is to find all deployed assets and make sure that each has
        an `AssetVersion` marked as `deployed=True` '''
        deployed_assets = Asset.objects.filter(
            _deployment_data__contains='backend')
        assets_to_fix = deployed_assets.exclude(asset_versions__deployed=True)
        unknown_deployed_version_count = 0
        fixed_count = 0
        self.stdout.write('Found {} assets to fix'.format(
            assets_to_fix.count()))
        for asset in assets_to_fix:
            try:
                deployed_version = asset._deployment_data['version']
            except KeyError:
                self.stderr.write(
                    u'Asset {}: malformed deployment data'.format(
                        asset.uid))
                continue
            if deployed_version == 0:
                unknown_deployed_version_count += 1
                continue
            if isinstance(deployed_version, basestring) and \
                    deployed_version.startswith('v'):
                query_field = 'uid'
            else:
                query_field = '_reversion_version_id'
            try:
                deployed_version_obj = asset.asset_versions.get(
                    **{query_field: deployed_version})
            except AssetVersion.DoesNotExist:
                self.stderr.write(
                    u'Asset {}: deployed version {} does not exist'.format(
                        asset.uid, deployed_version))
                continue
            # This is why we're here...
            assert deployed_version_obj.deployed == False
            deployed_version_obj.deployed = True
            deployed_version_obj.save()
            fixed_count += 1
        if fixed_count:
            self.stdout.write('Fixed {} assets'.format(fixed_count))
        if unknown_deployed_version_count:
            self.stdout.write('Skipped {} assets whose deployed versions were '
                              'unknown'.format(unknown_deployed_version_count))
